import asyncio
import base64
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, AsyncMock

TEST_DIRECTORY = tempfile.TemporaryDirectory()
os.environ['DATABASE_URL'] = 'sqlite:///' + str(Path(TEST_DIRECTORY.name) / 'test.db').replace('\\', '/')
os.environ['SECRET_KEY'] = 'test-secret-only-used-with-temporary-database'
os.environ['GROQ_API_KEY'] = 'test-groq'
os.environ['NVIDIA_API_KEY'] = 'test-nvidia'
os.environ['AGENTROUTER_API_KEY'] = ''
os.environ['TAVILY_API_KEY'] = ''

from fastapi.testclient import TestClient
from app.main import app
from app import models
from app.database import Base, engine, SessionLocal
from app.services import providers, rag_service, context_service
from app.services import web_search
from app.config import settings


def tearDownModule():
    engine.dispose()
    TEST_DIRECTORY.cleanup()


class PipelineTests(unittest.TestCase):
    def test_generation_lease_conflicts_expiry_and_token_ownership(self):
        from datetime import datetime, timedelta
        from fastapi import HTTPException
        from app.services import generation_lock
        chat = self.chat()
        token = generation_lock.acquire(chat)
        with self.assertRaises(HTTPException) as conflict:
            generation_lock.acquire(chat)
        self.assertEqual(conflict.exception.status_code, 409)
        self.assertEqual(self.send(chat, 'busy', web_search='off').status_code, 409)
        self.assertEqual(self.client.get(f'/chats/{chat}/messages', headers=self.headers).json(), [])
        generation_lock.release(chat, 'wrong-token')
        with SessionLocal() as db:
            lease = db.get(models.GenerationLease, chat)
            self.assertEqual(lease.token, token)
            lease.expires_at = datetime.utcnow() - timedelta(seconds=1)
            db.commit()
        replacement = generation_lock.acquire(chat)
        generation_lock.release(chat, token)
        with SessionLocal() as db:
            self.assertEqual(db.get(models.GenerationLease, chat).token, replacement)
        generation_lock.release(chat, replacement)

    def test_invalid_image_rolls_back_message_and_releases_lease(self):
        chat = self.chat()
        result = self.send(chat, 'describe', model='groq::meta-llama/llama-4-scout-17b-16e-instruct',
                           image_url='data:image/png;base64,bm90IGEgcG5n', web_search='off')
        self.assertEqual(result.status_code, 400, result.text)
        with SessionLocal() as db:
            self.assertEqual(db.query(models.Message).filter_by(chat_id=chat).count(), 0)
            self.assertIsNone(db.get(models.GenerationLease, chat))
        self.assertTrue(self.events(self.send(chat, 'Remember: retry works'))[-1]['done'])

    def test_vercel_rejects_ephemeral_storage_and_weak_secret(self):
        from app.config import Settings
        with patch.dict(os.environ, {'VERCEL': '1'}):
            with self.assertRaisesRegex(ValueError, 'persistent PostgreSQL'):
                Settings(_env_file=None, database_url='sqlite:///./chat.db', secret_key='x' * 40)
            with self.assertRaisesRegex(ValueError, 'random SECRET_KEY'):
                Settings(_env_file=None, database_url='postgresql://localhost/test', secret_key='weak')
            with self.assertRaisesRegex(ValueError, 'random SECRET_KEY'):
                Settings(_env_file=None, database_url='postgresql://localhost/test', secret_key='super-secret-key-change-in-production-abc123xyz789')
            config = Settings(_env_file=None, database_url='postgresql://localhost/test', secret_key='x' * 40)
            self.assertTrue(config.database_url.startswith('postgresql://'))

    def setUp(self):
        Base.metadata.drop_all(engine)
        Base.metadata.create_all(engine)
        self.client = TestClient(app)
        self.headers = self.register('alice@example.com')
        self.other_headers = self.register('bob@example.com')

    def register(self, email):
        response = self.client.post('/auth/register', json={'email': email, 'password': 'testing-password'})
        self.assertEqual(response.status_code, 200, response.text)
        return {'Authorization': 'Bearer ' + response.json()['access_token']}

    def chat(self, headers=None):
        response = self.client.post('/chats', headers=headers or self.headers, json={'default_model': 'nvidia::meta/llama-3.1-8b-instruct'})
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()['id']

    def send(self, chat_id, content, **kwargs):
        return self.client.post(f'/chats/{chat_id}/messages', headers=self.headers, json={'content': content, **kwargs})

    def events(self, response):
        self.assertEqual(response.status_code, 200, response.text)
        return [json.loads(frame[6:]) for frame in response.text.split('\n\n') if frame.startswith('data: ')]

    def test_authentication_and_ownership(self):
        chat = self.chat()
        self.assertEqual(self.client.get('/chats').status_code, 401)
        self.assertEqual(self.client.get('/chats', headers={'Authorization': 'Bearer broken'}).status_code, 401)
        for suffix in ['', '/messages', '/documents']:
            self.assertEqual(self.client.get(f'/chats/{chat}{suffix}', headers=self.other_headers).status_code, 404)
        self.assertEqual(self.client.post(f'/chats/{chat}/messages', headers=self.other_headers, json={'content': 'hello'}).status_code, 404)

    def test_memory_survives_new_chat_and_toggle(self):
        first = self.chat()
        events = self.events(self.send(first, 'Remember: I prefer Python examples.'))
        self.assertTrue(events[0]['memory_saved'])
        self.assertTrue(events[-1]['done'])
        second = self.chat()
        captured = []
        async def fake_stream(model, messages):
            captured.append((model, messages))
            yield 'A Python example.'
        with patch.object(providers, 'stream_chat', fake_stream):
            self.events(self.send(second, 'Help me code'))
            self.events(self.send(second, 'Explain a loop', use_memory=False))
        self.assertEqual(captured[0][0], 'nvidia::meta/llama-3.1-8b-instruct')
        self.assertIn('I prefer Python examples.', captured[0][1][0]['content'])
        self.assertNotIn('Saved memories (user-provided)', captured[1][1][0]['content'])
        self.assertIn('Help me code', str(captured[1][1]))
        memory = self.client.get('/memories', headers=self.headers).json()[0]
        self.assertEqual(self.client.get('/memories', headers=self.other_headers).json(), [])
        self.assertEqual(self.client.delete('/memories/' + memory['id'], headers=self.other_headers).status_code, 404)
        self.assertEqual(self.client.delete('/memories/' + memory['id'], headers=self.headers).status_code, 200)

    def test_rag_duplicate_names_citations_delete_and_persistence(self):
        chat = self.chat()
        other_chat = self.chat(self.other_headers)
        ids = []
        for text in [b'Project Orion uses a cobalt cooling system at 17 degrees.', b'Project Vega uses a helium cooling system at 28 degrees.']:
            r = self.client.post(f'/chats/{chat}/documents', headers=self.headers, files={'file': ('notes.txt', text, 'text/plain')})
            self.assertEqual(r.status_code, 200, r.text)
            ids.append(r.json()['id'])
        captured = []
        async def fake_stream(model, messages):
            captured.extend(messages)
            yield 'Orion uses cobalt [1].'
        with patch.object(providers, 'stream_chat', fake_stream):
            events = self.events(self.send(chat, 'What cooling system does Orion use?'))
        self.assertIn('cobalt', captured[0]['content'])
        self.assertTrue(events[0]['sources'])
        history = self.client.get(f'/chats/{chat}/messages', headers=self.headers).json()
        self.assertTrue(history[-1]['sources'])
        # A new session sees the index, and another chat cannot retrieve it.
        with SessionLocal() as db:
            self.assertTrue(rag_service.query(db, chat, 'Orion cobalt'))
            self.assertEqual(rag_service.query(db, other_chat, 'Orion cobalt'), [])
            self.assertEqual(len(rag_service.query(db, chat, 'Summarize these documents')), 2)
        captured.clear()
        with patch.object(providers, 'stream_chat', fake_stream):
            disabled = self.events(self.send(chat, 'What is the Orion cooling system?', use_rag=False))
        self.assertEqual(disabled[0]['sources'], [])
        self.assertNotIn('Retrieved document excerpts', captured[0]['content'])
        self.client.delete(f'/chats/{chat}/documents/{ids[0]}', headers=self.headers)
        with SessionLocal() as db:
            self.assertEqual(db.query(models.DocumentChunk).filter_by(document_id=ids[0]).count(), 0)
            self.assertEqual(rag_service.query(db, chat, 'cobalt'), [])
            self.assertTrue(rag_service.query(db, chat, 'helium'))
        self.client.delete(f'/chats/{chat}', headers=self.headers)
        with SessionLocal() as db:
            self.assertEqual(db.query(models.DocumentChunk).count(), 0)
            self.assertEqual(db.query(models.MessageDetails).count(), 0)

    def test_image_saved_private_and_cascades(self):
        chat = self.chat()
        png = b'\x89PNG\r\n\x1a\nmock-image'
        async def fake_image(*args):
            return base64.b64encode(png).decode(), 'image/png'
        with patch('app.services.image_service.generate', fake_image):
            result = self.client.post('/images/generate', headers=self.headers, json={'chat_id': chat, 'prompt': 'A forest'})
        self.assertEqual(result.status_code, 200, result.text)
        url = result.json()['url']
        self.assertEqual(self.client.get(url, headers=self.headers).content, png)
        self.assertEqual(self.client.get(url, headers=self.other_headers).status_code, 404)
        self.assertEqual(self.client.get(url).status_code, 401)
        history = self.client.get(f'/chats/{chat}/messages', headers=self.headers).json()
        self.assertEqual(len(history), 2)
        self.assertEqual(history[-1]['image_url'], url)
        self.client.delete(f'/chats/{chat}', headers=self.headers)
        self.assertEqual(self.client.get(url, headers=self.headers).status_code, 404)
        with SessionLocal() as db:
            self.assertEqual(db.query(models.GeneratedImage).count(), 0)

    def test_errors_and_validation(self):
        chat = self.chat()
        self.assertEqual(self.send(chat, ' ').status_code, 422)
        self.assertEqual(self.send(chat, 'hello', model='unknown::test').status_code, 400)
        self.assertEqual(self.send(chat, 'image', image_url='https://example.com/picture.png').status_code, 400)
        unsupported = self.client.post(f'/chats/{chat}/documents', headers=self.headers, files={'file': ('virus.exe', b'abc')})
        self.assertEqual(unsupported.status_code, 415)
        bad_pdf = self.client.post(f'/chats/{chat}/documents', headers=self.headers, files={'file': ('broken.pdf', b'abc')})
        self.assertEqual(bad_pdf.status_code, 400)
        async def failed_stream(*args):
            yield 'partial'
            raise RuntimeError('Provider unavailable')
        with patch.object(providers, 'stream_chat', failed_stream):
            events = self.events(self.send(chat, 'hello'))
        self.assertEqual(events[-1]['error'], 'Provider unavailable')
        history = self.client.get(f'/chats/{chat}/messages', headers=self.headers).json()
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]['role'], 'user')

    def test_context_is_bounded_and_keeps_recent_complete_turns(self):
        history = [models.Message(role=role, content=f'{i} ' + 'x' * 2000) for i in range(50) for role in ['user', 'assistant']]
        messages, count, _, _ = context_service.build_messages(history, 'Latest question', [], [])
        self.assertLess(sum(len(m['content']) for m in messages), 24000)
        self.assertLess(count, len(history))
        self.assertEqual(messages[-2]['role'], 'assistant')
        self.assertTrue(messages[-2]['content'].startswith('49 '))
        self.assertEqual(messages[-1]['content'], 'Latest question')

    def test_context_budget_with_large_input_memory_and_documents(self):
        memories = [models.Memory(content='A saved preference ' + 'x' * 980) for _ in range(100)]
        sources = [{'number': i + 1, 'filename': 'notes.txt', 'text': 'y' * 1200} for i in range(4)]
        messages, _, used_sources, memory_count = context_service.build_messages([], 'z' * 16000, memories, sources)
        self.assertLessEqual(sum(len(m['content']) for m in messages), 24000)
        self.assertEqual(messages[0]['content'].count('"citation":'), len(used_sources))
        self.assertGreater(memory_count, 0)

    def test_provider_transport_status_and_broken_stream(self):
        import httpx
        real_client = httpx.AsyncClient
        captured = []
        def handler(request):
            captured.append((str(request.url), json.loads(request.content)))
            return httpx.Response(200, text='data: {"choices":[{"delta":{"content":"Hello"}}]}\n\ndata: [DONE]\n\n')
        async def collect():
            return [delta async for delta in providers.stream_chat('nvidia::meta/llama-3.1-8b-instruct', [{'role': 'user', 'content': 'Hi'}])]
        with patch.object(providers.httpx, 'AsyncClient', lambda **kw: real_client(transport=httpx.MockTransport(handler), **kw)):
            self.assertEqual(asyncio.run(collect()), ['Hello'])
        self.assertIn('integrate.api.nvidia.com/v1/chat/completions', captured[0][0])
        self.assertEqual(captured[0][1]['model'], 'meta/llama-3.1-8b-instruct')
        def denied(request):
            return httpx.Response(401, text='secret key must never appear in errors')
        with patch.object(providers.httpx, 'AsyncClient', lambda **kw: real_client(transport=httpx.MockTransport(denied), **kw)):
            with self.assertRaisesRegex(RuntimeError, 'rejected the API key'):
                asyncio.run(collect())
        def broken(request):
            return httpx.Response(200, text='data: {"choices":[{"delta":{"content":"Partial"}}]}\n\n')
        with patch.object(providers.httpx, 'AsyncClient', lambda **kw: real_client(transport=httpx.MockTransport(broken), **kw)):
            with self.assertRaisesRegex(RuntimeError, 'ended unexpectedly'):
                asyncio.run(collect())

    def test_automatic_search_is_injected_cited_and_saved(self):
        chat = self.chat()
        sources = [{"kind": "web", "title": "Official release", "url": "https://example.com/release", "text": "The current release is version 9.", "excerpt": "The current release is version 9.", "published_date": "2026-10-16"}]
        captured = []
        async def answer(model, messages):
            captured.extend(messages)
            yield 'Version 9 [1](https://example.com/release).'
        planner = AsyncMock(return_value=[web_search.SearchRequest(query="latest release")])
        searcher = AsyncMock(return_value=sources)
        with patch.object(settings, 'tavily_api_key', 'test-tavily'), patch.object(web_search, 'plan_search', planner), patch.object(web_search, 'search', searcher), patch.object(providers, 'stream_chat', answer):
            events = self.events(self.send(chat, 'What is the latest release?'))
        planner.assert_awaited_once()
        searcher.assert_awaited_once()
        self.assertTrue(any(e.get('status') == 'searching' for e in events))
        self.assertIn('https://example.com/release', captured[0]['content'])
        self.assertIn('Web search status: completed', captured[0]['content'])
        history = self.client.get(f'/chats/{chat}/messages', headers=self.headers).json()
        self.assertEqual(history[-1]['sources'][0]['kind'], 'web')
        self.assertEqual(history[-1]['sources'][0]['url'], 'https://example.com/release')
        self.assertEqual(self.client.get(f'/chats/{chat}/messages', headers=self.other_headers).status_code, 404)

    def test_search_skips_when_not_needed_disabled_or_saving_memory(self):
        chat = self.chat()
        planner = AsyncMock(return_value=[])
        searcher = AsyncMock()
        async def answer(*args):
            yield '4'
        with patch.object(settings, 'tavily_api_key', 'test-tavily'), patch.object(web_search, 'plan_search', planner), patch.object(web_search, 'search', searcher), patch.object(providers, 'stream_chat', answer):
            self.events(self.send(chat, 'What is 2 + 2?'))
            self.events(self.send(chat, 'Hello', web_search='off'))
            self.events(self.send(chat, 'Remember: I like brief answers.'))
        planner.assert_awaited_once()
        searcher.assert_not_awaited()

    def test_search_failure_warns_and_continues_honestly(self):
        chat = self.chat()
        captured = []
        async def answer(model, messages):
            captured.extend(messages)
            yield 'I could not verify the current release.'
        with patch.object(settings, 'tavily_api_key', 'test-tavily'), patch.object(web_search, 'plan_search', AsyncMock(return_value=[web_search.SearchRequest(query='latest release')])), patch.object(web_search, 'search', AsyncMock(side_effect=RuntimeError('Tavily is rate limited.'))), patch.object(providers, 'stream_chat', answer):
            events = self.events(self.send(chat, 'Find the latest release'))
        self.assertTrue(any('rate limited' in e.get('warning', '') for e in events))
        self.assertIn('Web search status: failed', captured[0]['content'])
        self.assertTrue(events[-1]['done'])
        self.assertEqual(events[-1]['sources'], [])

    def test_search_planner_uses_recent_context_validates_and_caps_tools(self):
        call = {'function': {'name': 'tavily_search', 'arguments': json.dumps({'query': 'NVIDIA latest news', 'topic': 'news', 'time_range': 'last 7 days'})}}
        planner = AsyncMock(return_value={'tool_calls': [call, call, call]})
        history = [models.Message(role='user', content='What is new from NVIDIA?')]
        with patch.object(providers, 'complete_chat', planner):
            requests = asyncio.run(web_search.plan_search('nvidia::openai/gpt-oss-20b', 'What about today?', history))
        self.assertEqual(len(requests), 1)
        self.assertEqual(requests[0].time_range, 'week')
        self.assertIn('What is new from NVIDIA?', planner.call_args.args[1][1]['content'])
        self.assertEqual(planner.call_args.kwargs['tools'][0]['function']['name'], 'tavily_search')
        bad = {'function': {'name': 'run_shell', 'arguments': '{}'}}
        with patch.object(providers, 'complete_chat', AsyncMock(return_value={'tool_calls': [bad]})):
            with self.assertRaisesRegex(RuntimeError, 'invalid search request'):
                asyncio.run(web_search.plan_search('groq::openai/gpt-oss-20b', 'Hello', []))

    def test_tavily_transport_bounds_results_sanitizes_errors_and_urls(self):
        import httpx
        real_client = httpx.AsyncClient
        captured = []
        def handler(request):
            captured.append(request)
            return httpx.Response(200, json={'results': [
                {'title': 'Official page', 'url': 'https://example.com/news', 'content': 'x' * 5000},
                {'url': 'javascript:alert(1)', 'content': 'bad'},
                {'url': 'http://127.0.0.1/private', 'content': 'private'},
                {'url': 'http://user:password@example.com', 'content': 'credentials'},
            ]})
        with patch.object(settings, 'tavily_api_key', 'test-tavily'), patch.object(web_search.httpx, 'AsyncClient', lambda **kw: real_client(transport=httpx.MockTransport(handler), **kw)):
            sources = asyncio.run(web_search.search(web_search.SearchRequest(query='latest release', topic='news', time_range='day')))
        self.assertEqual(len(sources), 1)
        self.assertEqual(len(sources[0]['text']), 1200)
        self.assertEqual(captured[0].headers['Authorization'], 'Bearer test-tavily')
        payload = json.loads(captured[0].content)
        self.assertNotIn('api_key', payload)
        self.assertEqual(payload['time_range'], 'day')
        self.assertEqual(payload['max_results'], 4)
        def denied(request):
            return httpx.Response(401, text='test-tavily must not leak')
        with patch.object(settings, 'tavily_api_key', 'test-tavily'), patch.object(web_search.httpx, 'AsyncClient', lambda **kw: real_client(transport=httpx.MockTransport(denied), **kw)):
            with self.assertRaisesRegex(RuntimeError, '^Tavily rejected the API key'):
                asyncio.run(web_search.search(web_search.SearchRequest(query='test query')))

    def test_search_secrets_and_context_budget(self):
        self.assertNotIn('tvly-dev-abcdefghijklmnop', web_search.redact_secrets('Search tvly-dev-abcdefghijklmnop'))
        sources = [{'kind': 'web', 'number': i + 1, 'title': 'Page', 'url': f'https://example.com/{i}', 'text': 'x' * 1200} for i in range(8)]
        messages, _, used, _ = context_service.build_messages([], 'y' * 16000, [], sources, web_status='completed')
        self.assertLessEqual(sum(len(m['content']) for m in messages), 24000)
        self.assertEqual(messages[0]['content'].count('"citation":'), len(used))

    def test_image_transport_validates_live_payload_and_pending_response(self):
        import httpx
        from app.services import image_service
        real_client = httpx.AsyncClient
        calls = []
        encoded = base64.b64encode(b'\xff\xd8\xffimage-bytes').decode()
        def handler(request):
            calls.append(request)
            if request.method == 'POST':
                payload = json.loads(request.content)
                self.assertEqual(payload['cfg_scale'], 1)
                self.assertNotIn('mode', payload)
                return httpx.Response(202, headers={'nvcf-reqid': '1234-abcd'})
            if len(calls) == 2:
                return httpx.Response(202)  # Poll responses can omit the ID header.
            return httpx.Response(200, json={'artifacts': [{'base64': encoded, 'finishReason': 'SUCCESS'}]})
        async def no_sleep(*args):
            pass
        with patch.object(image_service.httpx, 'AsyncClient', lambda **kw: real_client(transport=httpx.MockTransport(handler), **kw)), patch.object(image_service.asyncio, 'sleep', no_sleep):
            data, mime = asyncio.run(image_service.generate('A teacup', 1024, 1024, image_service.IMAGE_MODEL))
        self.assertEqual(mime, 'image/jpeg')
        self.assertEqual(data, encoded)
        self.assertEqual(len(calls), 3)


if __name__ == '__main__':
    unittest.main()

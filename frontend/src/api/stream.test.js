import test from 'node:test';
import assert from 'node:assert/strict';
import { readChatStream } from './stream.js';

function response(text, size = 1) {
  const bytes = new TextEncoder().encode(text);
  return new Response(new ReadableStream({
    start(controller) {
      for (let i = 0; i < bytes.length; i += size) controller.enqueue(bytes.slice(i, i + size));
      controller.close();
    },
  }));
}

test('handles split UTF-8 characters and CRLF SSE frames', async () => {
  const events = [];
  await readChatStream(response('data: {"delta":"Hello 🌍"}\r\n\r\ndata: {"done":true,"message_id":"saved"}\r\n\r\n'), e => events.push(e));
  assert.equal(events[0].delta, 'Hello 🌍');
  assert.equal(events[1].message_id, 'saved');
});

test('surfaces upstream errors after partial text', async () => {
  await assert.rejects(readChatStream(response('data: {"delta":"partial"}\n\ndata: {"error":"quota exceeded"}\n\n', 8), () => {}), /quota exceeded/);
});

test('does not treat an interrupted response as saved', async () => {
  await assert.rejects(readChatStream(response('data: {"delta":"partial"}\n\n'), () => {}), /before the answer was saved/);
});

test('retains search progress, warnings and refreshed source metadata before a saved reply', async () => {
  const events = [];
  const frames = [
    { meta: true, sources: [] },
    { status: 'searching', message: 'Searching the web...' },
    { warning: 'One search failed.' },
    { meta: true, sources: [{ kind: 'web', url: 'https://example.com' }] },
    { delta: 'Verified answer' },
    { done: true, message_id: 'saved' },
  ];
  await readChatStream(response(frames.map(event => `data: ${JSON.stringify(event)}\n\n`).join(''), 3), event => events.push(event));
  assert.deepEqual(events, frames);
});

# Pipeline tests

Run from `backend`:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

The suite creates a temporary SQLite database and fake provider credentials before importing the application. It never reads or changes the application's chat database and never calls paid APIs. Provider streaming and image responses are mocked at the network/service boundary.

Coverage includes authentication, account isolation, cross-chat memory, disabled memory, document retrieval, citations surviving reload, duplicate filenames, deleting indexed chunks, private generated images, cascading chat deletion, context limits, provider routing, malformed input and interrupted streams.

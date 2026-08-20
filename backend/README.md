# CYA backend

## Local development

SQLite is the default storage backend. Starting the application automatically creates
`backend/data/cya.db`; no database service or storage configuration is required.

```bash
cd backend
python -m pip install -r requirements.txt -r requirements-dev.txt
uvicorn app:app --reload --port 3000
```

In a separate terminal, start the frontend:

```bash
cd frontend
npm run dev -- --strictPort
```

Set `DEBUG=true` to use built-in placeholder images instead of calling OpenAI
image generation or downloading remote placeholder URLs.

Set `CYA_SQLITE_PATH` to use a different database file.

Run the backend tests with:

```bash
python -m pytest tests
```

## MongoDB storage

To use the retained MongoDB implementation, set:

```text
CYA_STORAGE_BACKEND=mongodb
MONGODB_CONNECTION_STRING=...
CLUSTER=...
COLLECTION=...
```

The HTTP API is identical for both storage backends. Existing MongoDB saves are not
copied into SQLite automatically.

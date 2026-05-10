# Development Workflow

## Setup

```bash
make setup
make up
```

The `.env` file is local-only and must not be committed. Phase 0 does not require AWS, OCI, Claude, or OpenAI credentials.

## Common Commands

```bash
make compose-config
make ps
make logs
make backend-test
make backend-lint
make frontend-lint
make down
```

## Backend Conventions

- Add provider SDK logic only under `backend/collectors`.
- Add deterministic findings under `backend/findings`.
- Keep risk scoring under `backend/scoring`.
- Keep API schemas close to the API boundary.
- Keep database models under `backend/models`.

## Security Workflow

- Never commit `.env`.
- Use read-only cloud credentials for inventory collection.
- Separate test and production cloud accounts.
- Log operational events without credentials or secrets.

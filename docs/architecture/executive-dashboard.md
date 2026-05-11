# Executive Dashboard

## Purpose

The Phase 8 executive dashboard is the first Next.js user interface for Northbound Control Tower. It consumes the existing FastAPI APIs from Phases 2-7 and presents cloud scores, findings, inventory, risks, and trends without adding new backend scope.

## Sections

- Login: authenticates through `POST /api/v1/auth/login` and loads the current user from `GET /api/v1/auth/me`.
- Overview: shows the overall cloud operational score and domain scores.
- Risk summary: shows critical, high, open findings, connected cloud accounts, and detected providers.
- Inventory: lists normalized AWS and OCI resources with client-side filters.
- Findings: lists deterministic findings with filters and a safe detail panel for evidence and recommendations.
- Scores: visualizes domain scores, score history, and severity distribution.
- Risks: prioritizes the top active findings by severity and recency.
- Trends: summarizes resources by provider and category.

## API Dependencies

- `POST /api/v1/auth/login`
- `GET /api/v1/auth/me`
- `GET /api/v1/resources`
- `GET /api/v1/findings`
- `GET /api/v1/findings/summary`
- `GET /api/v1/scores/latest`
- `GET /api/v1/scores/summary`
- `GET /api/v1/scores/history`
- `GET /api/v1/cloud-accounts`

## Data Flow

Browser login stores the JWT for the local MVP. The dashboard reads the token, calls the backend APIs with a bearer token, renders empty states when datasets are absent, and redirects to `/login` when the backend returns `401`.

The frontend does not calculate findings or scores. It only derives display counts such as public resources, untagged resources, and local table filters from backend-provided normalized data.

## Security Considerations

- JWT tokens are not logged.
- API errors are rendered without exposing tokens or secrets.
- Cloud credential fields are not displayed in the dashboard.
- Finding evidence is rendered as escaped JSON text, never as HTML.
- LocalStorage token storage is accepted only for this local Phase 8 MVP. Production should move authentication to secure, httpOnly, same-site cookies with CSRF protections.

## Known Limitations

- Client-side filtering is suitable for the current MVP but should move to server-side pagination and filtering as data volume grows.
- The dashboard does not implement finding status updates yet.
- The dashboard does not calculate scores or run findings; those actions remain backend/API workflows.
- No paid or external frontend monitoring is introduced in this phase.

## Future Improvements

- Add server-side pagination and filter query support.
- Add role-aware status update actions for ADMIN and ANALYST users.
- Add account and provider selectors.
- Replace localStorage auth with secure cookie sessions.
- Add Playwright smoke tests for login and dashboard rendering.

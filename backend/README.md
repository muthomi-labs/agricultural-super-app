# Backend

## Purpose

The backend provides the server-side application for the **Agricultural Super App**. It exposes the platform's capabilities to the frontend over a REST API and acts as the single source of truth for business logic and data.

## Status

| Item | Status |
| --- | --- |
| Technology stack | Flask, SQLAlchemy, Marshmallow, PostgreSQL (SQLite for tests), JWT auth, Flask-Mail, Pillow |
| Models (`app/models/`) | Done — audited against `docs/schema.dbml`, verified |
| Schemas (`app/schemas/`) | Done — verified via live model round-trips |
| Application factory, config | Done |
| Auth (register/login/JWT, password reset, change-password) | Done — see "Password policy" and "Email" below |
| Role-based admin system | Done — see "Admin access" below |
| Image uploads (real device files, not URLs) | Done — see "Image uploads" below |
| Routes — auth, users, posts, comments, communities, messages, admin, uploads, stories, notifications, AI, channels | Done |
| Migrations | Flask-Migrate/Alembic, migration history committed under `migrations/versions/` |
| API docs | Flasgger/Swagger UI at `/apidocs/`, spec at `/apispec.json` — see "API documentation" below |
| Tests | 830+ passing — see "Testing" |
| CI | `../.github/workflows/backend-ci.yml` — tests, migrations, and Swagger boot check on every push/PR |

See `docs/TECHNICAL_DEBT.md` for known limitations and their priority.

## Getting started

```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# edit .env: set real SECRET_KEY, JWT_SECRET_KEY, and DATABASE_URL

export FLASK_APP=wsgi.py
flask db upgrade       # applies the migration history already committed under migrations/versions/

flask run              # or: python wsgi.py
```

(`flask db init`/`flask db migrate` are only for starting a *new* project or adding a *new* schema
change — this repo's migration history already exists and is committed, so a fresh clone only ever
needs `flask db upgrade`.)

`GET /health` returns `{"status": "ok"}` once the server is running.

**Presenting this project?** See [`docs/DEMO.md`](docs/DEMO.md) — includes a live demo script (`scripts/demo.py`) and a guide for what to show a mixed classmate/mentor audience.

## API surface

Full reference with request/response examples for every endpoint: **[`docs/API.md`](docs/API.md)**.

Quick summary — all routes are under `/api`, except `/health`:

| Resource | Routes |
| --- | --- |
| Auth | `POST /api/auth/register`, `POST /api/auth/login`, `GET /api/auth/me`, `POST /api/auth/forgot-password`, `POST /api/auth/reset-password`, `PUT /api/auth/change-password` |
| Users | `GET /api/users/<id>`, `PUT /api/users/me/profile`, `POST\|DELETE /api/users/<id>/follow` |
| Posts | `GET\|POST /api/posts`, `GET\|PUT\|DELETE /api/posts/<id>`, `POST /api/posts/<id>/images`, `DELETE /api/posts/<id>/images/<id>`, `GET\|POST /api/posts/<id>/comments`, `POST\|DELETE /api/posts/<id>/like`, `POST\|DELETE /api/posts/<id>/save`, `POST\|DELETE /api/posts/<id>/repost` |
| Comments | `PUT\|DELETE /api/comments/<id>` |
| Communities | `GET\|POST /api/communities`, `GET\|PUT\|DELETE /api/communities/<id>`, `POST\|DELETE /api/communities/<id>/members` |
| Messaging | `GET\|POST /api/conversations`, `GET /api/conversations/<id>`, `GET\|POST /api/conversations/<id>/messages`, `PATCH /api/messages/<id>/read` |
| Stories | `GET\|POST /api/stories`, `DELETE /api/stories/<id>` — see "Stories" below for the 24h expiration mechanism |
| Notifications | `GET /api/notifications`, `GET /api/notifications/unread-count`, `PATCH /api/notifications/<id>/read`, `PATCH /api/notifications/read-all` |
| AI Farming Assistant | `POST /api/ai/assistant` (stateless one-shot), `GET\|POST /api/ai/conversations`, `GET\|DELETE /api/ai/conversations/<id>`, `POST /api/ai/conversations/<id>/messages` (`?stream=true` for SSE) — see "AI Farming Assistant" below |
| Multi-channel access (SMS/USSD/voice) | `POST /api/channels/sms`, `POST /api/channels/ussd`, `POST /api/channels/voice` — see "Multi-channel access" below |
| Uploads | `POST /api/uploads` (multipart image upload), `POST /api/uploads/video`, `GET /api/uploads/<filename>` |
| Admin (requires `role=admin`) | `GET /api/admin/stats`, `GET /api/admin/users`, `GET /api/admin/users/<id>`, `PATCH /api/admin/users/<id>` |

Authenticated routes require `Authorization: Bearer <token>`, issued by `/api/auth/register` or `/api/auth/login`.

Every error response is a consistent JSON envelope: `{"error": "message", "details": {...optional...}}`.

`DELETE /api/posts/<id>` requires the caller to be the post's author, a global admin
(`role=admin`), or an admin member of the community the post belongs to (community admins cannot
delete posts outside their own community). See `app/services/post_service.py::_assert_can_delete_post`.

## API documentation

Interactive Swagger UI, generated from the real routes and kept in sync with them automatically:
`GET /apidocs/` (spec JSON at `/apispec.json`). Authenticated routes are marked accordingly, and
Swagger UI's "Authorize" button accepts a `Bearer <token>` value to try them directly. This is the
authoritative, always-current reference; `docs/API.md` is a hand-written narrative companion.

## Password policy

Passwords (registration, reset, and change-password) must be 8+ characters and include an
uppercase letter, a lowercase letter, a number, and a special character. The single source of
truth is `app/validators.py` (mirrored on the frontend in `frontend/src/lib/passwordPolicy.js`
for live UI feedback — the backend re-validates independently and is the real enforcement point).

## Admin access

There is intentionally no public "sign up as admin" path. To grant admin access, promote an
existing user's `role` column to `admin` directly in the database (e.g. via `flask shell` or a
one-off script) — never via an API route. `admin_required` (`app/auth/decorators.py`) is the
actual security boundary enforced on every `/api/admin/*` route; any frontend admin-nav hiding
is UX only.

## Image and video uploads

`POST /api/uploads` accepts a multipart image file (JPEG/PNG/WebP, validated by real content via
Pillow, not by extension/filename), re-encodes it (strips embedded metadata). Images are capped at
5MB.

`POST /api/uploads/video` accepts a multipart video file (MP4/MOV/WebM, for Reels/FarmClips) up to
50MB, validated by a magic-byte check on the container format (there's no video-processing
dependency in this project to decode/re-encode it like images, so this is a narrower guarantee than
the image path's full re-encode).

**Persistence:** when `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, and `SUPABASE_STORAGE_BUCKET`
are all set, both image and video uploads go to a Supabase Storage bucket — this is what production
actually uses, and it's required there: Render's disk is ephemeral and wipes on every redeploy, so
without Supabase configured, uploaded files silently vanish the next time the service deploys, with
no error at upload time. When any of the three is unset (the local-dev default), uploads fall back
to local disk under `UPLOAD_FOLDER` (defaults to `<instance>/uploads`) — fine for development,
**not durable in production**. See `app/services/upload_service.py`.

`MAX_CONTENT_LENGTH` (env-overridable, default 50MB) is the app-wide Flask request-body ceiling;
each upload type still enforces its own stricter limit inside `upload_service.py`.

## AI Farming Assistant

Provider-agnostic: `app/services/ai_service.py` is the single entry point every caller (the web
routes below, and the SMS/USSD channels — see "Multi-channel access") goes through; it resolves
whichever `AIProvider` is configured (`app/services/ai_providers.py`) and never lets the frontend
or any channel talk to a provider directly. Select the provider with `AI_PROVIDER`
(`ollama` (default, local/free, needs `ollama serve` running), `anthropic`, or `gemini`) and
`AI_MODEL`; `GEMINI_API_KEY`/`ANTHROPIC_API_KEY` as needed. Gemini has a genuinely free tier (no
billing setup) — production uses `gemini-3.1-flash-lite` specifically for its higher free-tier
quota over plain `flash` tiers and because it doesn't spend hidden "thinking" tokens on simple
questions (measured directly during development, not assumed).

Two request shapes: `POST /api/ai/assistant` is stateless (no history persisted, single question
in/answer out) and includes an in-process cache for standalone single-question requests (same
question + language → same cached reply for up to 6h, never for multi-turn context). The
`/api/ai/conversations/*` routes persist real conversation history; `POST .../messages?stream=true`
streams the reply incrementally via Server-Sent Events.

Language handling mirrors whichever language the farmer's current message is written in (English,
Kiswahili, or a natural mix), falling back to the account's saved `User.language` only when the
message itself gives no signal — this takes priority over the saved preference, not the other way
around. The system prompt also explicitly tolerates typos/phonetic spelling/informal grammar
without commenting on it.

## Stories

Stories expire 24 hours after creation. This is enforced at **read time**, not by a background
job: every query in `app/services/story_service.py` filters `expires_at > now()` directly, so
correctness never depends on a cron worker actually running (Render's free plan has none scheduled
by default). A `cleanup_expired_stories()` housekeeping function exists to actually delete expired
rows from the database, but it's optional cleanup, never load-bearing for correctness — an
unexpired-looking story can never be served even if that job hasn't run in a while.

## Multi-channel access

`POST /api/channels/{sms,ussd,voice}` let farmers reach the same AI Farming Assistant over basic
phones — no separate AI implementation; `app/services/channel_service.py` wraps a farmer's message
with a short-answer framing hint and calls `ai_service.ask_assistant()` unchanged, so language
handling, typo tolerance, and caching all apply automatically.

- **SMS**: inbound message → AI reply → outbound send via the `SmsProvider` interface
  (`app/services/channel_providers.py`). No real provider is wired up yet (`NullSmsProvider` always
  raises, deliberately — the response reports `delivered: false` with a clear reason rather than
  claiming a message was sent that wasn't).
- **USSD**: a stateless state machine parsing Africa's Talking-style accumulated `text` input
  (e.g. `"1*How often should I water tomatoes"`). Weather and market prices explicitly return "not
  yet available" — this app has no such data source, and nothing is fabricated to fill the menu.
  Response length is capped by `USSD_MAX_RESPONSE_LENGTH` (default 182, override via env — not a
  hardcoded assumption about one telecom's limit).
- **Voice**: architecture only — `SpeechToTextProvider`/`TextToSpeechProvider` interfaces exist
  (`app/services/channel_providers.py`) with `Null*` stubs; the route returns a plain 501
  "not yet available" rather than faking transcription or audio.

**Security:** these routes can't use JWT (telecom webhooks don't carry a browser session) — they're
protected instead by `CHANNEL_WEBHOOK_SECRET`, checked via the `X-Channel-Webhook-Secret` header or
a `?secret=` query param. If that env var is unset, **every** request is rejected, in every
environment including local dev, not just production — there is no bypass mode. Also rate-limited
per phone number (`CHANNEL_RATE_LIMIT_MAX_REQUESTS`/`CHANNEL_RATE_LIMIT_WINDOW_SECONDS`, in-process
— single-instance protection only, matching this deployment's `WEB_CONCURRENCY=1`; would need
Redis or equivalent for a multi-instance deployment, not introduced here since it isn't needed yet).
A phone number is never automatically linked to an existing `User` account — `PhoneIdentity.user_id`
stays null unless a future, separate, explicitly-verified linking flow sets it.

No real telecom provider (Africa's Talking, Twilio, etc.), speech-to-text, or text-to-speech service
is integrated. The interfaces are ready for one; provisioning an account and implementing a concrete
provider class is a deliberately separate, later decision.

## Email (password reset delivery)

Password-reset emails are sent via Flask-Mail over standard SMTP — any provider works (Gmail,
Outlook, a transactional service, etc.); there is no provider-specific logic. Set `MAIL_SERVER`,
`MAIL_PORT`, `MAIL_USE_TLS`/`MAIL_USE_SSL`, `MAIL_USERNAME`, `MAIL_PASSWORD`, and
`MAIL_DEFAULT_SENDER` in `.env` (see `.env.example` for a Gmail App Password example). If any of
`MAIL_SERVER`/`MAIL_USERNAME`/`MAIL_PASSWORD` is unset, email is treated as "not configured": the
reset token is still issued (so the flow can still be completed out-of-band), but no email is
sent — and the response to the client is identical either way, to avoid leaking whether an email
address is registered. **As of this MVP, no real SMTP credentials have been configured in this
environment, so live email delivery has not been verified end-to-end** — the send path itself is
covered by automated tests (`tests/unit/test_email_service.py`,
`tests/unit/test_auth_service.py::TestRequestPasswordReset`) using Flask-Mail's in-memory test
transport.

## Testing

```bash
pip install -r requirements-dev.txt
pytest                    # runs the full suite with coverage (see pytest.ini)
pytest tests/unit         # fast, no HTTP: business logic only
pytest tests/integration  # full request/response cycle through real routes
```

Tests run against in-memory SQLite by default (see `TestingConfig` in
`app/config.py`) — no database setup required to run them.

- `tests/unit/` — one file per service (`app/services/`), calling
  functions directly. Fast, and pinpoints exactly which function broke.
- `tests/integration/` — one file per resource, hitting real routes
  through Flask's test client. Confirms the HTTP wiring (status codes,
  auth enforcement, JSON shapes) on top of logic already proven at the
  unit level.
- `tests/conftest.py` — shared fixtures, including factory fixtures
  (`create_user`, `register_user`) for building test data without
  duplicating setup code across test files.

A coverage report is written to `htmlcov/index.html` after each run.

## Database Responsibility

- Own all database access and data integrity on behalf of the application.
- Enforce the data model defined in `docs/schema.dbml`.
- Apply schema changes through versioned migrations (Alembic, via Flask-Migrate).
- Prevent secrets and plain-text passwords from ever being stored or logged.

## Relationship with Frontend

- The frontend consumes the backend API; the backend never renders UI.
- Both live in the same repository but as separate application folders (`backend/` and `frontend/`).
- CORS is configured via `CORS_ORIGINS` in `.env` to allow the SPA's origin.
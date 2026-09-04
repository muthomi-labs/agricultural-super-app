# Technical Debt Register

Each entry: description, impact, recommended solution, priority, target milestone.
Do not delete resolved items — move them to a "Resolved" section with the
resolving commit/PR reference so history isn't lost.

---

## Open

### 3. `role` has no database-level enforcement

**Description:** `UserSchema.role` is now restricted to `farmer`/`expert`
via `validate.OneOf(...)` (added while building auth — see
`app/schemas/user_schema.py`), which closes the privilege-escalation
path through the registration API. But the `users.role` column itself is
still a free-text `varchar(30)` with no `CheckConstraint` or enum type at
the database level. Any code path that writes to this column outside
the schema (a future admin script, a bulk import, a bug in a new
endpoint) is not protected by that validation.

**Impact:** Low today (registration is currently the only write path to
`role`), but the protection is API-layer-only, not defense-in-depth.

**Recommended solution:** Add `db.CheckConstraint("role IN ('farmer', 'expert', 'admin')", name="valid_role")` (or a native Postgres `ENUM` type) at the model level, via migration.

**Priority:** Medium.

**Target milestone:** Before any second write path to `role` is built (e.g. an admin-promotion endpoint).

### 4. No admin bootstrap mechanism

**Description:** `role == "admin"` is checked throughout the service
layer as an authorization override, but there is currently no way to
create an admin account except direct database access
(`UPDATE users SET role = 'admin' WHERE id = ...`).

**Impact:** Low — expected for MVP — but worth having a deliberate answer
before this goes anywhere near production.

**Recommended solution:** A CLI command (`flask create-admin`) or a
one-time seed script, not an HTTP endpoint (an admin-promotion endpoint
would just recreate the same privilege-escalation risk closed in item 3
above, one layer up).

**Priority:** Low.

**Target milestone:** Before production deployment.

### 5. JWTs cannot be revoked

**Description:** Access tokens are stateless and signed, verified only
against `JWT_SECRET_KEY` and their own `exp` claim — there is no
server-side token store, so there is no way to invalidate a specific
token before it expires. `is_active` is re-checked on every request
(see `app/auth/decorators.py`), which handles *account* deactivation,
but a stolen-but-still-valid token for an active account cannot be
individually revoked, and there is no logout endpoint (logout is purely
a client-side "discard the token" action).

**Impact:** Medium — bounded by `JWT_ACCESS_TOKEN_EXPIRES_SECONDS`
(currently 24h), but a real "log out everywhere" or "I think my token
leaked" story requires either short-lived tokens + refresh tokens, or a
server-side blocklist.

**Recommended solution:** Add a refresh-token flow (short-lived access
token, longer-lived refresh token stored server-side and revocable) when
the mobile/SPA client needs "stay logged in" behavior beyond 24h.

**Priority:** Medium.

**Target milestone:** Before this ships with real user accounts.

### 6. Production config has no startup validation

**Description:** `ProductionConfig` accepts `SECRET_KEY`/`JWT_SECRET_KEY`
falling back to the insecure `dev-secret-key-change-me` default if the
environment variables are simply forgotten at deploy time — there's
nothing that stops the app from booting in that state.

**Impact:** High *if* it happens (tokens signed with a known default
secret are forgeable), but requires an operational mistake to trigger.

**Recommended solution:** In `create_app()`, when `config_name ==
"production"`, assert `SECRET_KEY`/`JWT_SECRET_KEY` are set and don't
match their dev defaults; raise on startup rather than serving traffic
insecurely.

**Priority:** Medium — cheap to fix, worth doing before first deploy.

**Target milestone:** Before production deployment.

### 7. `Message.is_read` has no `read_at` timestamp

*(Carried over from the original schema-layer review — still open.)*
A boolean captures *that* a message was read, not *when*. Fine for an
unread-count badge; insufficient for "seen 2 hours ago" UI, which the
messaging feature will likely want eventually.

**Priority:** Low. **Target milestone:** When read receipts UI is built.

### 8. `datetime.utcnow()` is deprecated (Python 3.12+)

**Found during:** Running the test suite — surfaced as a `DeprecationWarning`
on every single test that touches a timestamped row (370+ warnings in
the unit suite alone).

**Description:** Every model's `default=datetime.utcnow` (12 models) and
`message_service.py`'s manual `conversation.updated_at =
datetime.utcnow()` use naive (non-timezone-aware) datetimes. Python 3.12
deprecated `datetime.utcnow()` in favor of `datetime.now(timezone.utc)`,
which is timezone-aware. Notably, `app/auth/jwt.py` already does this
correctly (`datetime.now(timezone.utc)`) — the models are the
inconsistent ones.

**Impact:** None today (it still works, just emits a warning). Real risk
is comparing a naive and an aware datetime somewhere down the line,
which raises `TypeError` at runtime rather than failing predictably —
and the warning is currently just noise in the test output, which makes
it easy to stop noticing a *new*, unrelated deprecation warning once
this one is expected background noise.

**Recommended solution:** Replace `default=datetime.utcnow` with
`default=lambda: datetime.now(timezone.utc)` (or equivalent) across all
12 models and `message_service.py`, consistent with `app/auth/jwt.py`'s
existing pattern. Requires a migration if columns need to change from
`TIMESTAMP` to `TIMESTAMP WITH TIME ZONE` to actually store the tzinfo
rather than silently dropping it.

**Priority:** Low — cosmetic today, but cheap to fix and gets more
annoying to retrofit the longer timestamped data accumulates.

**Target milestone:** Next time any model file is touched for an
unrelated change; not urgent enough to justify a dedicated pass across
12 files on its own.

### 9. Video uploads are validated by magic bytes only, not re-encoded

**Found during:** Full-repository security audit, 2026-09-04.

**Description:** `POST /api/uploads/video` checks the container format
via a magic-byte/box-header sniff (`app/services/upload_service.py`)
but, unlike the image upload path (which decodes and re-encodes every
file via Pillow, stripping anything embedded outside the actual pixel
data), has no equivalent decode/re-encode step. A well-formed
MP4/MOV/WebM container carrying a malicious payload elsewhere in the
stream would pass validation.

**Impact:** Low today — uploaded video is only ever played back via a
`<video>` tag, never executed or parsed by a vulnerable server-side
tool. Would matter more if video were ever transcoded server-side or
opened by less-defensive tooling.

**Recommended solution:** Add a real video validation/transcode step
(e.g. via ffmpeg) if video ever gains more trust downstream.
Deliberately not added now — it's a new, fairly heavy dependency for a
risk that's currently low, and adding dependencies without a concrete
need was explicitly out of scope for the audit pass that found this.

**Priority:** Low. **Target milestone:** If/when video is processed
server-side for any reason (thumbnailing, transcoding, moderation).

### 10. Community and post search endpoints don't exist

**Found during:** Full-repository frontend/backend audit, 2026-09-04.

**Description:** `GET /api/users?search=` is real (ILIKE-backed).
There is no equivalent for communities or posts — the frontend's
"Search" page only searches users; community/post discovery is
list-and-scroll only.

**Impact:** Low-medium UX gap, not a defect — nothing is broken, the
app just doesn't have a feature its "global search" framing might
imply.

**Recommended solution:** Add `?search=` to `GET /api/communities`
(and, if needed, posts) mirroring `user_service.py`'s existing ILIKE
pattern.

**Priority:** Low. **Target milestone:** When community/post discovery
becomes a real user complaint, not preemptively.

### 11. Some list endpoints return unbounded or fully-nested collections

**Found during:** Full-repository backend audit, 2026-09-04.

**Description:** `CommunitySchema.members` dumps the entire member
list on every community read, and `message_service.list_conversations`/
`list_messages` have no pagination at all.

**Impact:** Low today at this app's scale; would degrade for a
community or conversation with a large member/message count.

**Recommended solution:** Paginate both, consistent with how
`post_service.list_posts` already does it.

**Priority:** Low. **Target milestone:** Before any community/
conversation is expected to have hundreds+ of members/messages.

### 12. No real telecom, speech-to-text, or text-to-speech provider is configured

**Found during:** Multi-channel access implementation, 2026-09-04.

**Description:** `app/services/channel_providers.py` defines
`SmsProvider`/`SpeechToTextProvider`/`TextToSpeechProvider` interfaces
with `Null*` implementations that deliberately raise/return "not
configured" rather than pretending to work. `POST /api/channels/sms`
computes a real AI reply but cannot actually deliver it over SMS;
`POST /api/channels/voice` returns a plain 501.

**Impact:** None today — this is the intended, honest state of an
MVP with no telecom account provisioned, not a bug.

**Recommended solution:** Implement a concrete `SmsProvider` (e.g. for
Africa's Talking or Twilio) once an account/credentials exist; the
interface is ready and requires no changes to `channel_service.py` or
`ai_service.py` to plug one in.

**Priority:** N/A — deliberately deferred, not a defect.
**Target milestone:** When a real telecom/STT/TTS account is
provisioned.

### 13. Channel rate limiter is single-instance only

**Found during:** Multi-channel access implementation, 2026-09-04.

**Description:** `app/services/channel_rate_limiter.py` is an
in-process, module-level sliding window (dict + lock) — correct and
sufficient for this deployment's `WEB_CONCURRENCY=1`, but would not
coordinate limits across multiple worker processes/instances.

**Impact:** None today. Would under-enforce the configured rate limit
(each instance would allow the full limit independently) if this ever
runs with more than one worker/instance.

**Recommended solution:** Move to a shared store (Redis, or the
database) if this deployment ever scales beyond a single instance.
Deliberately not done now — no such need exists yet, and Redis would
be a new piece of infrastructure for a currently-hypothetical problem.

**Priority:** Low. **Target milestone:** Before `WEB_CONCURRENCY` (or
instance count) is ever increased above 1.

---

## Resolved

### R1. Inconsistent `nullable` on timestamp columns — RESOLVED 2026-08-20

Added `nullable=False` to every `created_at` / `updated_at` / `joined_at`
column across `Profile`, `Post`, `PostImage`, `Comment`, `Like`,
`Community`, `CommunityMember`, `UserFollow`, `Conversation`,
`ConversationParticipant`, and `Message`, matching the pattern `User`
already used. Safe to apply directly (no migration/backfill needed) since
no `migrations/` directory existed yet and no database had been created
against the prior schema.

**Verified by:** introspecting `Model.<column>.property.columns[0].nullable`
for all 18 affected columns (confirmed `False` on every one), and by a raw
`sqlalchemy.insert()` bulk-insert test that bypasses the ORM's Python-side
default — before the fix this would have silently written `NULL`; after
the fix it raises `IntegrityError` at the database level, as intended.

See original write-up below for full context on why this mattered.

### R2. Asymmetric relationship declaration on `ConversationParticipant.user` — RESOLVED 2026-08-20

Added `back_populates="conversation_participations"` on
`ConversationParticipant.user`, and added the matching
`User.conversation_participations` relationship (with
`cascade="all, delete-orphan"`, consistent with the other join-table
back-references like `community_memberships`).

**Verified by:** confirming the relationship resolves in both directions
(`user.conversation_participations[0]` and
`conversation_participant.user`), and confirming the cascade actually
deletes the child row when removed from the parent's collection — not
just that the attribute exists.

See original write-up below for full context.

---

## Original findings (for reference)

## 1. Inconsistent `nullable` on timestamp columns

**Found during:** Marshmallow schema layer review (models vs. `docs/schema.dbml`),
2026-08-20.

**Description:**
`User.created_at` and `User.updated_at` are declared `nullable=False`. Every
other model's timestamp columns are not:

- `Profile.created_at` / `updated_at`
- `Post.created_at` / `updated_at`
- `PostImage.created_at`
- `Comment.created_at` / `updated_at`
- `Like.created_at`
- `Community.created_at` / `updated_at`
- `CommunityMember.joined_at`
- `UserFollow.created_at`
- `Conversation.created_at` / `updated_at`
- `ConversationParticipant.joined_at`
- `Message.created_at`

All of these rely solely on `default=datetime.utcnow`, which is a
**Python-side** default applied by SQLAlchemy's ORM unit-of-work — it does
**not** translate into a `DEFAULT` clause or `NOT NULL` constraint at the
database level.

**Impact:**
Any write path that bypasses the ORM's normal `session.add()` /
autogenerated-INSERT flow — bulk inserts via `Table.insert()`, raw SQL,
data migrations, or a future seed/import script — can silently persist
`NULL` into these columns. Downstream code (e.g. sorting posts by
`created_at`, computing "joined X days ago") would then have to handle
`None`, or fail unexpectedly. `users` is the only table currently
protected against this at the schema level.

**Recommended solution:**
Add `nullable=False` to every timestamp column listed above, matching the
`users` table's pattern, via an Alembic migration (`ALTER COLUMN ... SET
NOT NULL`, after backfilling any existing `NULL` rows if migrating a
populated database). Consider also moving to `server_default=func.now()`
for `created_at` columns so the default is enforced by PostgreSQL itself
regardless of write path, with `default=datetime.utcnow` kept as a
Python-side convenience for pre-flush access to the value.

**Priority:** Medium — not a correctness bug today (the ORM always
supplies these values in the app's current single write path), but it's
a latent data-integrity gap that gets more expensive to fix the more rows
accumulate.

**Target milestone:** Before the first bulk-import, admin tooling, or
background job that writes to these tables outside a normal request/ORM
flow.

---

## 2. Asymmetric relationship declaration on `ConversationParticipant.user`

**Found during:** Same review as #1.

**Description:**
`ConversationParticipant.user = db.relationship("User")` has no
`back_populates`, unlike every other FK relationship in the codebase,
which is declared bidirectionally (e.g. `Post.user` /
`User.posts`).

**Impact:**
Low today — the relationship still works one-directionally. Risk is that
someone later adds a `User.conversation_participations` back-reference
with a different attribute name or `back_populates` target, silently
diverging from the pattern used everywhere else, rather than the mismatch
being caught immediately by SQLAlchemy's configuration checks.

**Recommended solution:**
Add `back_populates="participant_memberships"` (or similar) on both
sides, matching the existing convention.

**Priority:** Low — style/consistency only.

**Target milestone:** Next time `ConversationParticipant` or `User` is
touched for an unrelated change.

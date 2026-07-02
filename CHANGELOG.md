# Changelog

All notable changes to this project are documented here.

## Phase 1 — Project Foundation & Landing Page

- Set up the Flask application factory pattern (`app/__init__.py`) with
  environment-based configuration (`development`, `testing`, `production`).
- Added the `main` blueprint serving the public landing page.
- Wired up SQLAlchemy and Flask-Migrate against SQLite (`instance/fidelbridge.db`),
  with `DATABASE_URL` support for a future PostgreSQL migration.
- Built the Tailwind CSS design system: brand color palette (Dangote Blue +
  Amber accent), typography, reusable button/card components.
- Self-hosted Alpine.js and the Inter font (no external CDN dependency) via
  an `npm postinstall` script.
- Built the premium landing page: hero, featured categories, how it works,
  why FidelBridge, corporate section, testimonials, and final CTA.
- Added a responsive sticky navigation bar with a mobile menu, and a
  multi-column footer.
- Added custom 404 / 500 error pages.
- Added the initial Pytest suite covering the landing page and 404 handling.
- Added project documentation: README, PROJECT_STRUCTURE, INSTALLATION.

## Phase 2 — Authentication

- Added `User`, `CustomerProfile`, `ProfessionalProfile`, and `CorporateProfile`
  models (one `users` table with a `role` column, plus a 1:1 role-specific
  profile table) and generated the first Alembic migration.
- Added Customer, Professional, and Corporate registration flows behind a
  role-selection landing page (`/auth/register`), each with its own
  Flask-WTF form and validation (unique email, password confirmation).
- Added login (with "Remember Me"), logout, and Flask-Login session
  management; passwords are hashed with Werkzeug's `generate_password_hash`.
- Added a `role_required` decorator and per-role `customer`, `professional`,
  and `corporate` blueprints, each with a protected placeholder dashboard
  that redirects unauthenticated users to login and blocks the wrong role
  with a 403.
- Added a reusable Jinja macro library for styled form fields, checkboxes,
  and CSRF-expiry messaging, plus site-wide flash message rendering.
- Wired the navbar to reflect auth state (Log In/Get Started vs. a
  personalized greeting and Log Out) and pointed landing-page CTAs at the
  relevant registration forms.
- Added a 403 error page.
- Extended the Pytest suite to cover registration, login, logout, session
  protection, and role-based access control (12 tests total).

## Phase 3 — Customer Dashboard, Browse & Search

- Added a `Category` model and a `flask seed-categories` CLI command that
  idempotently seeds the 12 default service categories.
- Linked `ProfessionalProfile` to `Category` and added a required category
  picker to professional registration.
- Added a public `browse` blueprint: `/browse/categories` (category grid),
  `/browse/professionals` (search with keyword/category/city filters and
  pagination), and `/browse/professionals/<user_id>` (public professional
  profile page with a verification badge and an honest "Booking Coming
  Soon" / "Log In to Book" CTA rather than a fake working button).
- Reworked the landing page's category grid to pull from the database
  (single source of truth) and link each card to the matching search
  results; pointed the navbar "Services" link at the real search page.
- Added a shared, responsive dashboard shell (`dashboard/_shell.html`) with
  a sidebar that collapses into horizontally scrollable tabs on mobile, and
  rebuilt the customer dashboard on top of it with quick links and a
  category shortcut grid.
- Added a customer profile page (`/customer/profile`) to edit name, phone,
  address, city, and state.
- Extended the Pytest suite to cover category browsing, professional
  search/filtering, public profile pages, and customer profile editing
  (21 tests total).

## Phase 4 — Professional Dashboard, Portfolio & Verification

- Added `Skill`, `PortfolioItem`, and `Verification` models (all 1:1/1:many
  from `ProfessionalProfile`), plus `available_days` / `available_hours`
  columns for a simple weekly-availability tag (not a booking calendar —
  that's a later phase).
- Rebuilt the professional profile edit page on the shared dashboard shell,
  including a checkbox grid for available days.
- Added Skills management (add/remove tag-style skills) and Portfolio
  management (add/remove work samples with an optional photo).
- Added document Verification uploads (Government ID, Proof of Address,
  Certification, Other) with a pending/approved/rejected status shown to
  the professional; admin review comes in Phase 9.
- **Security**: verification documents are stored under `instance/uploads/`
  (outside `static/`, gitignored) and served only through an authenticated,
  ownership-checked download route — never through the public static file
  server. Portfolio photos, which are meant to be public, are the only
  uploads served from `static/`. All uploads are capped at 5&nbsp;MB, checked
  against an extension allow-list, and saved under randomly generated
  filenames (never the client-supplied name) to prevent path traversal and
  filename collisions.
- Added a profile-completion checklist to the professional dashboard
  (profile details / skill / portfolio item / verification doc), each item
  linking straight to the page that completes it.
- The public professional profile page now shows availability, skills, and
  a portfolio gallery when present.
- Extended professional search to also match on skill names.
- Extended the Pytest suite to cover profile editing (including a
  regression test that renders the page and checks the actual `checked`
  state of the availability checkboxes, not just the saved DB value —
  this caught a real bug, see below), skills, portfolio (with and without
  an image), and verification upload/download/ownership checks (30 tests
  total).

**Bug caught during manual verification:** WTForms gives `obj=` attribute
values priority over same-named keyword arguments whenever the object has
that attribute. `ProfessionalProfileForm(obj=professional, available_days=...)`
silently discarded the `available_days` list because `professional` already
has an `available_days` attribute (the raw stored string) — every checkbox
rendered unchecked on page reload even though the correct value was saved to
the database. Fixed by building the form from explicit keyword arguments
instead of `obj=`.

## Phase 5 — Corporate Dashboard & Service Requests

- Added a `CorporateRequest` model (`request_type`: procurement / facility
  management / janitorial / other; `status`: pending / in_progress /
  completed / cancelled) linked from `CorporateProfile`, plus
  address/city/state fields on `CorporateProfile` itself.
- Added a company profile edit page (`/corporate/profile`).
- Rebuilt the corporate dashboard on the shared shell with request-count
  stats (total/pending/in-progress/completed), three "Request a Service"
  quick-create cards (one per type), and a recent-requests list.
- Added a full request lifecycle for corporates: submit
  (`/corporate/requests/new`, with the type pre-selected when reached via a
  quick-create card), list with status-filter tabs
  (`/corporate/requests`), view details, and cancel a still-pending request.
  Fulfillment/assignment is admin territory (Phase 9) — corporates can only
  cancel, not mark in-progress/completed.
- Added a 400 error page (used when a non-pending request is cancelled).
- Extended the Pytest suite to cover profile editing, request submission,
  status filtering, cancellation (including that a non-pending request
  can't be cancelled, and that one corporate can't view or cancel another's
  request), and role isolation (40 tests total).

**Bug caught while writing tests, not the app itself:** the `app` pytest
fixture kept one Flask app context open for an entire test (`yield` sitting
inside `with application.app_context(): ...`). Because Flask reuses an
already-active app context instead of pushing a new one, every
`client.get()/post()` call in a test shared a single SQLAlchemy session —
so a direct DB write made via a separate `with app.app_context()` block
was invisible to a later `client.get()` in the same test, masked by that
shared session's stale identity-map cache. This didn't affect the running
app (real requests always get a fresh context and session), but it could
have hidden real bugs in future tests. Fixed by no longer holding an app
context open for the test body, so the test client's requests behave
exactly like production requests.

## Phase 6 — Booking System & Notifications

- Added a `Booking` model (customer ↔ professional, one row per job
  request) with a status lifecycle: `pending` → `accepted`/`rejected` by
  the professional, then `in_progress` → `completed`, or `cancelled` by
  the customer while still pending/accepted. Each transition is its own
  route/button (Accept, Decline, Mark as In Progress, Mark as Completed,
  Cancel) rather than a generic "update status" form, so each role can
  only take the actions that make sense for them.
- Added a `Notification` model and a `notify(user, message, link)` helper
  that queues a notification alongside whatever booking action triggered
  it (accept, reject, start, complete, cancel, and the original request),
  committed together in one transaction.
- Added a `notifications` blueprint: `/notifications` lists everything for
  the current user (any role), with mark-one-read and mark-all-read.
  Clicking a notification's "View" jumps straight to the relevant booking.
- Added a bell icon to the navbar (desktop and mobile) showing an unread
  badge, computed once per request via a context processor.
- The public professional profile's "Booking Coming Soon" placeholder from
  Phase 3 is now real: customers see "Request to Hire", which opens a
  booking form (`/customer/book/<professional_id>`) pre-scoped to that
  professional.
- Customer and professional dashboards now show real booking stats
  (active/completed for customers, new-request count for professionals)
  and a "recent bookings"/"recent job requests" list, replacing the
  Phase 1–5 placeholder zeros.
- Contact details (phone number) are only revealed to each side once a
  booking is accepted — not on the public profile, and not while a
  request is still pending.
- Extended the Pytest suite to cover the full accept → start → complete
  lifecycle, rejection, cancellation rules (only from pending/accepted,
  and only by the owning customer), cross-account access checks on
  bookings, and the notifications page (51 tests total).

## Phase 7 — Messaging

- Added `Conversation` (one per accepted booking, between the customer and
  professional on that job) and `Message` models.
- Added a `messages` blueprint: a conversation list (`/messages`, sorted by
  most recent activity, with an unread-count badge per thread), a chat
  interface (`/messages/<id>`), and `/messages/start/<booking_id>` which
  finds-or-creates the conversation for a booking.
- **Messaging only opens up once a booking is accepted** — same rule as
  the phone-number reveal from Phase 6 — so a customer can't message a
  professional (or vice versa) before there's an actual working
  relationship. "Message" buttons appear on the booking detail pages
  alongside the contact info, once unlocked.
- **Basic real-time updates via polling, not websockets**: the chat page
  polls a small JSON endpoint (`/messages/<id>/poll?since=<id>`) every 4
  seconds for newer messages and appends them live via vanilla JS
  (`app/static/js/chat.js`) — appropriate for MVP message volume without
  adding Flask-SocketIO/eventlet to the deployment.
- New messages create a `Notification` for the recipient too (reusing the
  Phase 6 system), and a separate envelope icon (distinct from the
  notification bell) shows an unread-message badge in the navbar and on
  both dashboards, replacing the last remaining placeholder "0" stat.
- Extended the Pytest suite to cover the accepted-only messaging gate,
  sending/receiving, read-state on view, the poll endpoint returning only
  messages newer than a given id, and cross-account access checks
  (60 tests total).

**Two real bugs caught while writing tests, not the app being wrong on
first try:**
1. `convo.updated_at = message.created_at` read `created_at` off a
   `Message` object that hadn't been flushed yet, so the column default
   hadn't run — it was still `None`, which violated the `NOT NULL`
   constraint on `updated_at` the moment the row was touched. Fixed by
   setting the timestamp explicitly instead of relying on an unflushed
   object's default.
2. Several test helpers registered a second account without logging out
   the first — since the registration routes redirect an already-
   authenticated user straight to their dashboard instead of processing
   the form, the second account was silently never created, and later
   assertions failed confusingly far from the real cause. Fixed by adding
   the missing `logout` calls; worth noting as a pattern for future test
   helpers in this codebase.

## Phase 8 — Ratings & Reviews, Search Filters & Sorting

- Added a `Review` model: one per completed `Booking` (unique on
  `booking_id`, so a job can only be rated once), 1–5 star rating plus an
  optional comment. `ProfessionalProfile` gets `average_rating` and
  `review_count` computed properties.
- Customers can leave a review from the booking detail page once (and only
  once) a booking reaches "Completed" — the form is replaced by the
  submitted review (stars + comment) after submission. Leaving a review
  notifies the professional.
- The public professional profile now shows the real average rating and
  star count instead of "No reviews yet", plus a full reviews list
  (reviewer name, stars, comment, date). Search result cards show the
  same star summary.
- Added a reusable `render_stars(rating)` Jinja macro
  (`app/templates/macros/stars.html`) so rating stars render identically
  everywhere they appear (search cards, profile page, booking review,
  dashboard).
- Extended professional search with a **State** filter (alongside the
  existing City filter — "Location Filters"), a **Minimum Rating** filter
  (4+ / 3+ stars), and a **Sort By** control (Most Relevant / Highest
  Rated / Most Reviews / Newest), all combinable and preserved across
  pagination. Rating-based filtering/sorting uses a SQL subquery
  (`AVG`/`COUNT` grouped by professional) joined into the search query, so
  it works correctly with the existing pagination rather than sorting only
  the current page in Python.
- Extended the Pytest suite to cover leaving a review (and being blocked
  before completion or on a second attempt), the review showing up on the
  public profile with the correct average, the review notification, and
  the new minimum-rating/sort-by/state search behavior (68 tests total).

## Phase 9 — Admin Dashboard

- Added an `admin` blueprint (`/admin/*`), gated by `role_required("admin")`,
  covering trust & safety, catalog management, account moderation, booking
  oversight, corporate request fulfillment, and platform reporting.
- **Professionals & verification**: a filterable (pending/verified/all)
  professional list, a detail page with Approve/Revoke Verification, and
  per-document Approve/Reject on uploaded verification files (rejection
  requires an `admin_notes` reason). Approving/revoking notifies the
  professional, linking to their public profile.
- **Categories**: full CRUD (`/admin/categories`) reusing the same
  `slugify()` helper (now moved to `app/utils/text.py` so both `seeds.py`
  and the admin form share one implementation instead of duplicating it).
  Deleting a category is blocked with a flash error if any professional is
  still assigned to it, rather than silently orphaning their `category_id`.
- **Users**: a searchable (name/email) and role-filterable list with
  Deactivate/Reactivate. Deactivating sets `is_active_account = False`,
  which already blocked login before this phase (Phase 2) — the admin UI
  is new, the enforcement was not. **Admins cannot deactivate other admins**
  through this UI (400) — there's no public admin sign-up route (see
  `flask create-admin` below), so removing the last admin account this way
  would be an unrecoverable lockout.
- **Bookings**: a status-filterable list, a detail page, and an admin-only
  "Cancel this booking" override for bookings not already
  completed/cancelled/rejected — notifies both the customer and the
  professional. This is a moderation escape hatch (e.g. a dispute), on top
  of the customer's own Phase 6 cancel flow, not a replacement for it.
- **Corporate requests**: a status-filterable list and a detail page with a
  full status-update form (Pending/In Progress/Completed/Cancelled). Unlike
  every other status transition in the app (booking accept/reject/start/
  complete, corporate request cancel), this is the one deliberately generic
  "set status to X" endpoint — admin's role here is total oversight/
  fulfillment tracking across all four states, not a constrained
  single-purpose action, so a generic endpoint (with server-side validation
  that the posted value is one of the four valid statuses) is the right
  shape rather than four near-identical single-purpose routes.
- **Reports** (`/admin/reports`): users by role, bookings by status,
  corporate requests by status, and top categories by professional count —
  each rendered as a simple CSS width-percentage bar chart (no JS charting
  library, consistent with the rest of the app's "plain HTML/CSS where it's
  good enough" approach), plus headline stats (verified professionals,
  average platform rating, total reviews, completed booking value).
- Added a `flask create-admin` CLI command (interactive prompts for email /
  full name / password, with hidden + confirmed password input) — there is
  intentionally no public admin registration route, so this is the only way
  to create the first admin account.
- No new migration was required — `flask db migrate` reported "No changes
  in schema detected"; every model Phase 9 needed (`User`, `Category`,
  `ProfessionalProfile`, `Verification`, `Booking`, `CorporateRequest`,
  `Review`) already existed from earlier phases.
- Extended the Pytest suite with `tests/test_admin.py` covering access
  control (non-admins get 403), professional verification approval,
  verification document approve/reject, category create/delete and the
  delete-blocked-by-assigned-professionals rule, user deactivate/reactivate
  and the can't-deactivate-another-admin rule, admin booking view/cancel,
  corporate request status updates (with notification), and the reports
  page (79 tests total).

## Phase 10 — UI Polish, Security, Performance & Deployment

- **Security headers on every response** (`X-Content-Type-Options`,
  `X-Frame-Options: DENY`, `Referrer-Policy`, `Permissions-Policy`, and a
  `Content-Security-Policy` scoped to self-hosted assets only), plus
  `Strict-Transport-Security` in production. The CSP allows
  `script-src 'unsafe-eval'` because Alpine.js's expression evaluator needs
  it, and `style-src 'unsafe-inline'` because the Phase 9 report bar charts
  use inline `width:` styles — both verified to still work with the CSP
  active (checked for zero browser console errors across the landing page,
  mobile nav, login, dashboards, and the reports page).
- **Rate limiting** (`Flask-Limiter`): login is capped at 10 attempts per
  minute and each registration form at 20 per hour, per IP, to blunt
  brute-force and spam without needing a CAPTCHA. A dedicated 429 error
  page matches the existing 400/403/404/500 pages. In-memory storage is
  fine for the current single-instance deployment (documented in
  `PRODUCTION_CHECKLIST.md` as something to revisit if the app ever scales
  to multiple instances, since in-memory limits don't share state across
  processes).
- **Cookie & transport hardening in production**: `SESSION_COOKIE_SECURE`,
  `REMEMBER_COOKIE_SECURE`, and `PREFERRED_URL_SCHEME=https` are only set
  in `ProductionConfig` (forcing them in development would break `flask
  run`'s plain-HTTP server). `ProxyFix` is applied in production so Flask
  correctly sees `https://` and the real client IP through Render's proxy,
  which both the secure-cookie logic and the rate limiter's per-IP keying
  depend on.
- **`ProductionConfig` refuses to boot with the default `SECRET_KEY`** —
  fails fast with a clear `RuntimeError` at startup instead of silently
  running with a well-known, insecure key.
- **Database indexes** added on the foreign keys and columns actually
  filtered/joined on in hot paths: booking status + both profile FKs,
  professional `category_id`/`is_verified`, a composite
  `(user_id, is_read)` index on notifications (the unread-count context
  processor runs this exact lookup on every authenticated page load),
  conversation participant columns, message `conversation_id`, corporate
  request status + FK, and review/verification `professional_profile_id`.
  Deliberately did **not** index `ProfessionalProfile.city`/`state` —
  search filters those with a `%term%` `ILIKE`, which a plain B-tree index
  can't accelerate anyway, so an index there would just be dead weight.
- **Cache-busted static assets**: `SEND_FILE_MAX_AGE_DEFAULT` now caches
  static files for a day (previously uncached), with a new
  `asset_url()` Jinja helper (`app/utils/assets.py`) that appends the
  file's mtime as a `?v=` query string — so `output.css`/`main.js`/vendored
  Alpine.js get aggressive caching without ever serving a stale copy after
  a deploy changes the file.
- **UI polish**: flash messages now fade/slide in and out (`x-transition`)
  instead of appearing instantly; every form submit button now shows a
  "Please wait…" state and disables itself the moment it's clicked
  (`app/static/js/main.js`, applied globally via a single `submit` event
  listener), both giving clearer feedback on slower connections and
  preventing accidental double-submits.
- **Deployment**: added `render.yaml` (a Render Blueprint — one web
  service plus a managed PostgreSQL database, with `SECRET_KEY`
  auto-generated and `DATABASE_URL` wired automatically), a `/healthz`
  endpoint for Render's health check, and `psycopg2-binary` in
  `requirements.txt` so the app can actually talk to Postgres in
  production (previously only SQLite's driver, which ships with Python,
  was available).
- Added a `PRODUCTION_CHECKLIST.md` covering secrets/config, database
  setup and backups, the security measures above, performance notes, and
  monitoring/operations — a punch list to work through before pointing a
  real domain at a deployment.
- No test changes were needed — Phase 10 is infrastructure/config/UI, not
  new user-facing behavior; the full 79-test suite continues to pass
  unchanged, and rate limiting is disabled in `TestingConfig`
  (`RATELIMIT_ENABLED = False`) so it doesn't interfere with tests that
  hit `/auth/login` more than 10 times.

## Phase 11 — Self-Service Password Reset

A manual security audit after Phase 10 (IDOR, CSRF, XSS, admin
authorization, upload handling — all clean, see the session notes) flagged
one real gap: there was no way for a user who forgot their password to
recover their account short of an admin touching the database directly.
This phase closes that gap.

- Added `User.reset_token` / `reset_token_expires_at` (indexed, 1-hour
  lifetime) plus `generate_reset_token()` / `clear_reset_token()` /
  `query_by_valid_reset_token()` helper methods on the model.
  **Requesting a new reset link invalidates any previous one** — token
  generation always overwrites the existing token/expiry rather than
  appending, so an old, possibly-leaked reset email stops working the
  moment a newer one is issued. Tokens are also **single-use**: a
  successful reset clears the token immediately.
- Added `/auth/forgot-password` (request a reset link) and
  `/auth/reset-password/<token>` (set a new password), both rate-limited
  (5/hour and 10/hour respectively) alongside the existing login/register
  limits from Phase 10.
- **The forgot-password response is identical whether or not the email
  has an account** ("If an account exists for that email, a reset link
  has been sent.") — same user-enumeration defense already used on login's
  generic "Incorrect email or password" message.
- Added `app/utils/mail.py`: a minimal `send_email()` that uses SMTP if
  `MAIL_SERVER` is configured (new env vars in `app/config.py`), and
  otherwise logs the message instead of failing. This means the full
  reset flow is testable and demoable in development without any real
  email provider — appropriate for an MVP where wiring up a transactional
  email service (SendGrid, SES, etc.) is a deploy-time decision, not a
  code change. `PRODUCTION_CHECKLIST.md` should be updated with real
  `MAIL_*` credentials before this is relied on in production.
- Added a "Forgot password?" link to the login page.
- Extended the Pytest suite with `tests/test_password_reset.py`: generic
  message for unknown emails, token generation for known emails, a full
  reset changes the password and old credentials stop working, invalid
  and expired tokens are rejected, tokens are single-use, and requesting
  a new link invalidates an older one (87 tests total).
- Verified live: submitted the forgot-password form, read the real reset
  link out of the (console-logged) email, followed it, set a new
  password, confirmed the old password now fails and the new one logs
  in, and confirmed reusing the same link afterward redirects back to
  "request a new one" instead of silently working twice.

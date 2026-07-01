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

# Project Structure

```
FIDEL_BRIDGE/
├── app/
│   ├── __init__.py            # Application factory (create_app)
│   ├── config.py              # Environment-based configuration classes
│   ├── extensions.py          # Shared Flask extension instances (db, migrate, login_manager)
│   ├── seeds.py                # Idempotent reference-data seeding (categories)
│   ├── blueprints/
│   │   ├── main/                # Public marketing pages (landing page, etc.)
│   │   ├── auth/                 # Registration, login, logout
│   │   ├── browse/               # Public category/professional search + profile pages
│   │   ├── customer/             # Customer dashboard, profile, bookings (protected, role=customer)
│   │   ├── professional/         # Professional dashboard, profile, bookings (protected, role=professional)
│   │   ├── corporate/            # Corporate dashboard (protected, role=corporate)
│   │   ├── notifications/        # Notification inbox (protected, any authenticated role)
│   │   └── messages/              # Conversations + chat (protected, any authenticated role)
│   │       ├── __init__.py
│   │       └── routes.py
│   ├── forms/
│   │   ├── auth.py            # Flask-WTF registration/login forms + validation
│   │   ├── customer.py        # Customer profile edit form
│   │   ├── professional.py    # Profile/skill/portfolio/verification-upload forms
│   │   ├── corporate.py       # Company profile + service-request forms
│   │   ├── booking.py         # Booking request form
│   │   └── message.py         # Chat message form
│   ├── models/
│   │   ├── __init__.py        # Imports every model so Flask-Migrate sees them
│   │   ├── roles.py           # Role constants (customer/professional/corporate/admin)
│   │   ├── user.py            # User model (auth, password hashing, Flask-Login)
│   │   ├── customer.py        # CustomerProfile (1:1 with User)
│   │   ├── professional.py    # ProfessionalProfile (1:1 with User, linked to Category)
│   │   ├── corporate.py       # CorporateProfile (1:1 with User)
│   │   ├── corporate_request.py  # CorporateRequest (1:many from CorporateProfile)
│   │   ├── category.py        # Category (service categories: Electricians, Plumbers, ...)
│   │   ├── skill.py           # Skill (1:many from ProfessionalProfile)
│   │   ├── portfolio.py       # PortfolioItem (1:many from ProfessionalProfile)
│   │   ├── verification.py    # Verification (uploaded doc + pending/approved/rejected status)
│   │   ├── booking.py         # Booking (customer <-> professional job request + status lifecycle)
│   │   ├── notification.py    # Notification (per-user, optionally linked to a booking)
│   │   ├── conversation.py    # Conversation (two users, one per accepted booking)
│   │   └── message.py         # Message (belongs to a Conversation)
│   ├── utils/
│   │   ├── decorators.py      # role_required(*roles) route decorator
│   │   ├── auth_helpers.py    # dashboard_url_for(user) role -> dashboard redirect
│   │   ├── uploads.py         # Secure file upload saving (random filenames, extension allow-list)
│   │   ├── notifications.py   # notify(user, message, link) helper
│   │   └── messaging.py       # unread_message_count(user) helper
│   ├── templates/
│   │   ├── base.html          # Shared HTML shell (head, nav, flash messages, footer, scripts)
│   │   ├── partials/
│   │   │   ├── navbar.html    # Sticky responsive nav (auth-aware)
│   │   │   ├── footer.html
│   │   │   └── flash_messages.html
│   │   ├── macros/
│   │   │   └── forms.html     # Reusable styled field/checkbox/error-banner macros
│   │   ├── dashboard/
│   │   │   └── _shell.html    # Shared responsive dashboard shell (sidebar -> mobile tabs)
│   │   ├── errors/
│   │   │   ├── 403.html
│   │   │   ├── 404.html
│   │   │   └── 500.html
│   │   ├── main/
│   │   │   └── index.html     # Landing page
│   │   ├── auth/
│   │   │   ├── register_choice.html
│   │   │   ├── register_customer.html
│   │   │   ├── register_professional.html
│   │   │   ├── register_corporate.html
│   │   │   └── login.html
│   │   ├── browse/
│   │   │   ├── categories.html
│   │   │   ├── professionals.html
│   │   │   └── professional_profile.html
│   │   ├── customer/
│   │   │   ├── dashboard.html
│   │   │   ├── profile.html
│   │   │   ├── book_professional.html  # Booking request form, reached from a profile page
│   │   │   ├── bookings.html           # List with status-filter tabs
│   │   │   └── booking_detail.html     # Detail + cancel (while pending/accepted)
│   │   ├── professional/
│   │   │   ├── dashboard.html     # Profile-completion checklist + stats
│   │   │   ├── profile.html
│   │   │   ├── skills.html
│   │   │   ├── portfolio.html
│   │   │   ├── verification.html
│   │   │   ├── bookings.html      # List with status-filter tabs
│   │   │   └── booking_detail.html  # Detail + Accept/Decline/Start/Complete
│   │   ├── corporate/
│   │   │   ├── dashboard.html     # Stats + quick-create cards + recent requests
│   │   │   ├── profile.html
│   │   │   ├── requests.html      # List with status-filter tabs
│   │   │   ├── request_form.html
│   │   │   └── request_detail.html
│   │   ├── notifications/
│   │   │   └── index.html         # Notification inbox, mark-one/mark-all read
│   │   └── messages/
│   │       ├── conversations.html # List, sorted by recency, with unread badges
│   │       └── conversation.html  # Chat thread + send form + polling script
│   └── static/
│       ├── src/input.css      # Tailwind source (edit this)
│       ├── css/output.css     # Compiled Tailwind CSS (generated, do not edit)
│       ├── js/main.js         # Site JavaScript
│       ├── js/chat.js         # Polls for new chat messages every 4s (no websockets)
│       ├── images/            # Static images / favicon
│       ├── vendor/alpinejs/   # Self-hosted Alpine.js (generated, do not edit)
│       ├── fonts/inter/       # Self-hosted Inter font files (generated, do not edit)
│       └── uploads/portfolio/ # Public portfolio photos (gitignored, runtime content)
├── instance/                  # SQLite DB + private verification-doc uploads (gitignored)
├── migrations/                # Flask-Migrate migration scripts
├── scripts/
│   └── copy-vendor.js         # Copies Alpine.js + Inter font from node_modules into app/static
├── tests/                     # Pytest test suite
├── run.py                     # Local development entry point
├── wsgi.py                    # Production entry point (gunicorn)
├── requirements.txt           # Production Python dependencies
├── requirements-dev.txt       # Adds pytest for local development
├── package.json               # Tailwind + vendor asset tooling
├── tailwind.config.js         # Design tokens (brand colors, fonts, shadows)
├── .flaskenv                  # Local Flask CLI environment variables
└── .env.example                # Template for secrets (copy to .env)
```

## Design Decisions

- **Application factory pattern** (`create_app`) so the app can be
  instantiated multiple times with different configs (development, testing,
  production) — required for clean testing and future scaling.
- **Blueprints** separate concerns by user-facing area: `main` (public
  pages), `auth` (registration/login/logout), `browse` (public category and
  professional search — not behind login, since discovery should be open),
  and one blueprint per role (`customer`, `professional`, `corporate`) for
  their dashboards. `admin` is added in Phase 9.
- **One `users` table, not a `Role` table**: `role` is a plain string column
  with a DB-level check constraint (`app/models/roles.py`). With a small,
  fixed set of roles this is simpler than a many-to-many `Role` table and
  avoids brittle SQLite/Alembic enum migrations.
- **Role-specific profile tables** (`CustomerProfile`, `ProfessionalProfile`,
  `CorporateProfile`) are 1:1 with `User`, so each role can carry different
  fields without a wide, mostly-null `users` table.
- **`role_required` decorator** wraps `flask_login.login_required` and
  checks `current_user.role`, so protected routes get both "must be logged
  in" and "must be the right role" in one line.
- **`Category` as its own table**, linked from `ProfessionalProfile`, rather
  than a hardcoded list — the same categories now drive the landing page,
  registration form, and search filters from one source of truth. Seeded
  via `flask seed-categories` (idempotent) rather than baked into a
  migration, since reference data and schema changes are different concerns.
- **Shared dashboard shell** (`dashboard/_shell.html`) factors out the
  sidebar-that-becomes-mobile-tabs layout so Phase 4/5 can reuse it for the
  professional and corporate dashboards instead of re-implementing it.
- **Booking status transitions are separate routes, not a generic "update
  status" endpoint.** Accept/Decline/Start/Complete/Cancel each check both
  the current status and who's allowed to make that specific transition
  (e.g. only the professional can accept; only the customer can cancel;
  cancel only works from pending/accepted). A single generic status-update
  route would let a client bypass those rules by just posting a different
  status value.
- **Notifications are queued, not sent, inside the same transaction as the
  action that triggers them** (`notify()` calls `db.session.add()` but
  never commits) — so a booking's status change and its notification are
  always consistent; there's no window where one succeeds and the other
  doesn't.
- **Contact details are revealed progressively**: a professional's phone
  number isn't on their public profile or visible to a customer whose
  request is still pending — it only appears once a booking is accepted,
  and only to the two parties involved.
- **Verification documents are never served from `static/`.** Portfolio
  photos are meant to be public, so they're saved under
  `app/static/uploads/portfolio/` and served directly. Verification
  documents (IDs, certificates) are sensitive, so they're saved under
  `instance/uploads/verifications/` — outside the static file server
  entirely — and only reachable through an authenticated route that checks
  the requester owns the document. Both upload paths use randomly
  generated filenames (never the client-supplied name) and an
  extension allow-list, enforced server-side regardless of what the
  browser's `<input accept>` hint suggests.
- **Availability is a filter tag, not a calendar.** `available_days` /
  `available_hours` are simple columns on `ProfessionalProfile` rather than
  a booking-calendar table — right-sized for "customers can see roughly
  when I work," with an actual scheduling system deferred to the booking
  phase if the product needs it later.
- **One `CorporateRequest` model with a `request_type` column**, not three
  separate tables for procurement/facility-management/janitorial. The three
  request types share every field (title, description, location, budget,
  preferred date, status) — only the label differs — so a single table with
  a type discriminator avoids duplicating the same schema three times.
- **Corporates can only cancel a pending request**, not move it to
  in-progress/completed themselves — that's fulfillment/admin territory
  (Phase 9). The cancel route 400s if called on a non-pending request
  instead of silently allowing it.
- **Messaging is gated on an accepted booking**, same rule as the phone
  reveal — `Conversation.booking_id` is unique, so each job gets at most
  one thread, found-or-created via `/messages/start/<booking_id>`.
- **Polling instead of websockets for "real-time" chat.** A 4-second poll
  against a small JSON endpoint is enough for expected MVP message
  volume and avoids adding Flask-SocketIO/eventlet (and the deployment
  complexity that brings on Render) for a feature that doesn't need
  sub-second latency yet.
- **SQLite now, PostgreSQL later**: `DATABASE_URL` is read from the
  environment, so switching to PostgreSQL in production is a config change,
  not a code change.
- **Self-hosted frontend assets**: Alpine.js and the Inter font are vendored
  into `app/static` via `npm install` (postinstall script) instead of loaded
  from a public CDN, avoiding a runtime dependency on third-party
  availability.

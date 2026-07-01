# Project Structure

```
FIDEL_BRIDGE/
├── app/
│   ├── __init__.py            # Application factory (create_app)
│   ├── config.py              # Environment-based configuration classes
│   ├── extensions.py          # Shared Flask extension instances (db, migrate, login_manager)
│   ├── blueprints/
│   │   ├── main/               # Public marketing pages (landing page, etc.)
│   │   ├── auth/                # Registration, login, logout
│   │   ├── customer/            # Customer dashboard (protected, role=customer)
│   │   ├── professional/        # Professional dashboard (protected, role=professional)
│   │   └── corporate/           # Corporate dashboard (protected, role=corporate)
│   │       ├── __init__.py
│   │       └── routes.py
│   ├── forms/
│   │   └── auth.py            # Flask-WTF registration/login forms + validation
│   ├── models/
│   │   ├── __init__.py        # Imports every model so Flask-Migrate sees them
│   │   ├── roles.py           # Role constants (customer/professional/corporate/admin)
│   │   ├── user.py            # User model (auth, password hashing, Flask-Login)
│   │   ├── customer.py        # CustomerProfile (1:1 with User)
│   │   ├── professional.py    # ProfessionalProfile (1:1 with User)
│   │   └── corporate.py       # CorporateProfile (1:1 with User)
│   ├── utils/
│   │   ├── decorators.py      # role_required(*roles) route decorator
│   │   └── auth_helpers.py    # dashboard_url_for(user) role -> dashboard redirect
│   ├── templates/
│   │   ├── base.html          # Shared HTML shell (head, nav, flash messages, footer, scripts)
│   │   ├── partials/
│   │   │   ├── navbar.html    # Sticky responsive nav (auth-aware)
│   │   │   ├── footer.html
│   │   │   └── flash_messages.html
│   │   ├── macros/
│   │   │   └── forms.html     # Reusable styled field/checkbox/error-banner macros
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
│   │   ├── customer/dashboard.html
│   │   ├── professional/dashboard.html
│   │   └── corporate/dashboard.html
│   └── static/
│       ├── src/input.css      # Tailwind source (edit this)
│       ├── css/output.css     # Compiled Tailwind CSS (generated, do not edit)
│       ├── js/main.js         # Site JavaScript
│       ├── images/            # Static images / favicon
│       ├── vendor/alpinejs/   # Self-hosted Alpine.js (generated, do not edit)
│       └── fonts/inter/       # Self-hosted Inter font files (generated, do not edit)
├── instance/                  # SQLite database file lives here (gitignored)
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
  pages), `auth` (registration/login/logout), and one blueprint per role
  (`customer`, `professional`, `corporate`) for their dashboards. `admin` is
  added in Phase 9.
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
- **SQLite now, PostgreSQL later**: `DATABASE_URL` is read from the
  environment, so switching to PostgreSQL in production is a config change,
  not a code change.
- **Self-hosted frontend assets**: Alpine.js and the Inter font are vendored
  into `app/static` via `npm install` (postinstall script) instead of loaded
  from a public CDN, avoiding a runtime dependency on third-party
  availability.

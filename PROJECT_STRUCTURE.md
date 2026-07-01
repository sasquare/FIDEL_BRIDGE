# Project Structure

```
FIDEL_BRIDGE/
├── app/
│   ├── __init__.py            # Application factory (create_app)
│   ├── config.py              # Environment-based configuration classes
│   ├── extensions.py          # Shared Flask extension instances (db, migrate)
│   ├── blueprints/
│   │   └── main/              # Public marketing pages (landing page, etc.)
│   │       ├── __init__.py
│   │       └── routes.py
│   ├── models/
│   │   └── __init__.py        # SQLAlchemy models (added from Phase 2 onward)
│   ├── templates/
│   │   ├── base.html          # Shared HTML shell (head, nav, footer, scripts)
│   │   ├── partials/
│   │   │   ├── navbar.html    # Sticky responsive navigation
│   │   │   └── footer.html
│   │   ├── errors/
│   │   │   ├── 404.html
│   │   │   └── 500.html
│   │   └── main/
│   │       └── index.html     # Landing page
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
- **Blueprints** separate concerns by user-facing area. Phase 1 only has
  `main` (public pages); `auth`, `customer`, `professional`, `corporate`,
  and `admin` blueprints are added in later phases.
- **SQLite now, PostgreSQL later**: `DATABASE_URL` is read from the
  environment, so switching to PostgreSQL in production is a config change,
  not a code change.
- **Self-hosted frontend assets**: Alpine.js and the Inter font are vendored
  into `app/static` via `npm install` (postinstall script) instead of loaded
  from a public CDN, avoiding a runtime dependency on third-party
  availability.

# Installation Guide

This guide walks through setting up FidelBridge locally from a clean clone.

## Prerequisites

- Python 3.11+
- Node.js 18+ and npm (for the Tailwind CSS build)
- Git

## 1. Clone and enter the project

```bash
git clone <repo-url>
cd FIDEL_BRIDGE
```

## 2. Create and activate a virtual environment

```bash
python -m venv venv

# macOS / Linux
source venv/bin/activate

# Windows (PowerShell)
venv\Scripts\Activate.ps1
```

You should see `(venv)` at the start of your terminal prompt.

## 3. Install Python dependencies

```bash
pip install -r requirements-dev.txt
```

## 4. Install frontend tooling and build CSS

```bash
npm install     # also self-hosts Alpine.js and the Inter font into app/static
npm run build    # compiles app/static/src/input.css -> app/static/css/output.css
```

Run `npm run watch` in a separate terminal while editing templates if you
want Tailwind to rebuild automatically.

## 5. Configure environment variables

```bash
cp .env.example .env
```

Open `.env` and set `SECRET_KEY` to a long random string. Never commit `.env`.

## 6. Create the database

```bash
flask db upgrade
```

This creates `instance/fidelbridge.db` with the `users`, `customer_profiles`,
`professional_profiles`, and `corporate_profiles` tables.

## 7. Run the app

```bash
flask run
```

Visit **http://127.0.0.1:5000** — you should see the FidelBridge landing page.

## Verifying the setup

- `flask run` should print `Running on http://127.0.0.1:5000` with no errors.
- The landing page should load with the navy/amber brand styling (not
  unstyled HTML — if the page looks unstyled, re-run `npm run build`).
- `http://127.0.0.1:5000/static/css/output.css` should return `200`.
- `http://127.0.0.1:5000/does-not-exist` should show the custom 404 page.
- Resizing the browser below ~1024px wide should collapse the nav into a
  hamburger menu that opens/closes on click.
- Visit `/auth/register`, create a Customer account, and confirm you land on
  `/customer/dashboard` with a "Hi, `<name>`" greeting in the nav.
- Log out, then log back in at `/auth/login` — you should return to the same
  dashboard.
- While logged in as a customer, visiting `/professional/dashboard` directly
  should show the 403 page.

## Running tests

```bash
pytest
```

All tests (`tests/test_landing_page.py`, `tests/test_auth.py`) should pass.

## Common Errors & Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `ModuleNotFoundError: No module named 'flask'` | Virtual environment not activated, or dependencies not installed | Activate `venv`, then re-run `pip install -r requirements-dev.txt` |
| Page loads but looks completely unstyled | `output.css` was never generated | Run `npm install && npm run build` |
| `flask: command not found` | Virtual environment not activated | Activate `venv` first |
| `sqlite3.OperationalError: unable to open database file` | `instance/` folder missing permissions | Delete `instance/` and restart `flask run` — the app recreates it automatically |
| Changes to Tailwind classes don't show up | CSS wasn't rebuilt | Run `npm run build`, or keep `npm run watch` running while you work |
| `.env` values not taking effect | `.env` not created, or Flask started before it was created | Confirm `.env` exists at the project root and restart `flask run` |
| `sqlite3.OperationalError: no such table: users` | Migrations were never applied | Run `flask db upgrade` |
| Registration/login form re-shows with no visible error after submitting | CSRF token expired (session too old, or form left open too long) | Refresh the page and submit again — the form now shows "Your session expired" when this happens |

# Installation Guide — Phase 1

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

## 6. Run the app

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

## Running tests

```bash
pytest
```

Both tests (`tests/test_landing_page.py`) should pass.

## Common Errors & Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `ModuleNotFoundError: No module named 'flask'` | Virtual environment not activated, or dependencies not installed | Activate `venv`, then re-run `pip install -r requirements-dev.txt` |
| Page loads but looks completely unstyled | `output.css` was never generated | Run `npm install && npm run build` |
| `flask: command not found` | Virtual environment not activated | Activate `venv` first |
| `sqlite3.OperationalError: unable to open database file` | `instance/` folder missing permissions | Delete `instance/` and restart `flask run` — the app recreates it automatically |
| Changes to Tailwind classes don't show up | CSS wasn't rebuilt | Run `npm run build`, or keep `npm run watch` running while you work |
| `.env` values not taking effect | `.env` not created, or Flask started before it was created | Confirm `.env` exists at the project root and restart `flask run` |

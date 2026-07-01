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
`professional_profiles`, `corporate_profiles`, and `categories` tables.

## 7. Seed the default service categories

```bash
flask seed-categories
```

This populates Electricians, Plumbers, Carpenters, and the other default
categories. It's safe to re-run — it skips categories that already exist.
Professional registration requires at least one category to exist.

## 8. Run the app

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
- Visit `/browse/categories` — you should see 12 category cards (if empty,
  run `flask seed-categories`).
- Register a Professional account and pick a category; then visit
  `/browse/professionals` and confirm the new professional appears and that
  filtering by category/city/keyword narrows the results.
- Click through to a professional's public profile page
  (`/browse/professionals/<id>`) and confirm it loads.
- As a customer, visit `/customer/profile`, change a field, save, and
  confirm the change persists after a page refresh.
- Register a Professional, then visit `/professional/profile` and check a
  few "Available Days" boxes, save, and confirm they're still checked after
  the page reloads (not just saved — actually re-checked on screen).
- Add a skill at `/professional/skills` and confirm it appears as a chip;
  remove it and confirm it disappears.
- Add a portfolio item with a photo at `/professional/portfolio`, and
  confirm the photo appears both there and on the public profile page.
- Upload a document at `/professional/verification` and confirm it shows
  "Pending"; click "View" and confirm the file downloads/opens.
- Log in as a *different* professional and try to guess another
  professional's verification document URL
  (`/professional/verification/<id>/download`) — it should 404, not serve
  the file.
- Register a Corporate account, and from `/corporate/dashboard`, click each
  of the three "Request a Service" cards (Procurement / Facility Management
  / Janitorial) and confirm the request type is pre-selected on the form.
- Submit a request, confirm it shows "Pending" on `/corporate/requests`,
  and that the status-filter tabs (Pending/In Progress/Completed/Cancelled)
  correctly show/hide it.
- Open the request's detail page and click "Cancel this request" — the
  status should change to "Cancelled" and the cancel option should
  disappear.
- Log in as a *different* corporate account and try to open the first
  corporate's request detail URL directly — it should 404.
- As a customer, open a professional's public profile and click "Request
  to Hire", fill in the form, and submit. Log in as that professional and
  confirm the notification bell shows an unread badge, the job appears
  under Job Requests, and the dashboard's "New Job Requests" count is 1.
- Accept the job, then Mark as In Progress, then Mark as Completed — after
  each step, confirm the customer sees a new notification and the status
  badge updates on both sides.
- Confirm the professional's phone number is hidden from the customer
  while the request is still "Pending", and appears once it's "Accepted".
- Try to accept an already-accepted booking directly via its accept URL —
  it should 400, not silently re-accept.
- As the customer, cancel a still-pending request from a *different*
  booking and confirm the professional gets a "cancelled" notification.
- Try visiting `/messages/start/<id>` for a booking that's still "Pending"
  — it should 400, since messaging only opens up once a booking is
  accepted.
- Once a booking is accepted, click "Message ..." from either side's
  booking detail page, send a message, and confirm it appears in the
  chat and the other party's message envelope icon shows an unread badge.
- **Real-time check**: open the conversation as both parties in two
  different browsers (or one normal + one incognito window). Send a
  message from one side, then watch the other side's open chat tab —
  within ~4 seconds the new message should appear without a page reload.
- Confirm a third account (not a participant in that booking) gets a 404
  when visiting the conversation URL directly.

## Running tests

```bash
pytest
```

All tests should pass (60 as of Phase 7, across `tests/test_landing_page.py`,
`tests/test_auth.py`, `tests/test_browse.py`, `tests/test_customer.py`,
`tests/test_professional.py`, `tests/test_corporate.py`,
`tests/test_booking.py`, and `tests/test_messaging.py`).

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
| Professional registration form shows no category options / fails validation | Categories were never seeded | Run `flask seed-categories` |
| Registration/login form re-shows with no visible error after submitting | CSRF token expired (session too old, or form left open too long) | Refresh the page and submit again — the form now shows "Your session expired" when this happens |

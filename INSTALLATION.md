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

## 8. Create your first admin account

```bash
flask create-admin
```

This prompts for an email, full name, and password (hidden input, confirmed
twice). There is no public admin sign-up route — this CLI command is the
only way to create an admin account.

## 9. Run the app

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
- Complete a booking end-to-end (accept → in progress → completed), then
  as the customer, leave a review from the booking detail page. Confirm
  the form disappears and the stars + comment show in its place, and that
  the professional gets a review notification.
- Visit that professional's public profile and confirm the "Rating"
  summary and the reviews list both show the new review.
- Try submitting a second review for the same booking (e.g. by resending
  the form) — it should 400, not create a duplicate.
- On `/browse/professionals`, try the **State** filter, the **Minimum
  Rating** filter, and each **Sort By** option (especially "Highest
  Rated") with a few reviewed professionals in the database, and confirm
  the results and their order change as expected.
- Log in with the admin account you created via `flask create-admin` and
  confirm `/admin/dashboard` loads with real stats (total users, pending
  verifications, pending corporate requests, active bookings).
- From `/admin/professionals`, open a pending professional and click
  "Approve Professional" — confirm the badge flips to "Verified", the
  button becomes "Revoke Verification", and the professional receives a
  notification.
- Upload a verification document as that professional, then as admin
  Approve one document and Reject another (with a reason). Confirm the
  approved one shows "Approved" and the rejected one shows the reason.
- From `/admin/categories`, create a new category, confirm it appears in
  the list and its slug looks right, then delete it — it should disappear.
- Try deleting a category that has a professional assigned to it — it
  should be blocked with a clear error instead of silently succeeding.
- From `/admin/users`, deactivate a customer or professional account, then
  try to log in as that user — login should be blocked. Reactivate it and
  confirm login works again.
- Try deactivating another admin account — it should 400, not succeed.
- From `/admin/bookings`, open a booking and use the admin "Cancel this
  booking" override — confirm both the customer and professional get a
  notification and the status updates to "Cancelled".
- From `/admin/corporate-requests`, open a request and change its status —
  confirm the corporate account gets a notification reflecting the new
  status.
- Visit `/admin/reports` and confirm the stat cards and bar charts reflect
  the current state of the database (e.g. verified professional count,
  bookings by status).
- Confirm a non-admin account gets a 403 when visiting any `/admin/*` URL
  directly.
- Open your browser's dev tools, load any page, and check the response
  headers for `Content-Security-Policy`, `X-Frame-Options: DENY`, and
  `X-Content-Type-Options: nosniff`. Confirm there are no CSP violations
  logged in the console (the mobile nav menu, flash-message dismiss, and
  the admin reports bar charts all depend on the CSP allowing Alpine.js
  and inline styles).
- On `/auth/login`, submit the wrong password 11 times in under a minute —
  the 11th attempt should show the custom "You're going a bit too fast"
  429 page, not a normal login retry.
- Submit any form (e.g. login) and confirm the submit button visibly
  disables and shows "Please wait…" the moment you click it.
- Visit `/healthz` and confirm it returns `{"status": "ok"}`.
- Reload any page and check that `/static/css/output.css` is requested
  with a `?v=<number>` query string, and that its response includes a
  `Cache-Control: public, max-age=86400` header.

## Running tests

```bash
pytest
```

All tests should pass (79 as of Phase 10, across `tests/test_landing_page.py`,
`tests/test_auth.py`, `tests/test_browse.py`, `tests/test_customer.py`,
`tests/test_professional.py`, `tests/test_corporate.py`,
`tests/test_booking.py`, `tests/test_messaging.py`, `tests/test_reviews.py`,
and `tests/test_admin.py`). Rate limiting is disabled in the test config
(`RATELIMIT_ENABLED = False`) so tests that log in more than 10 times don't
trip the production rate limit.

## Deploying to Render

1. Push this repository to GitHub.
2. In the Render dashboard, choose **New +** → **Blueprint**, and point it
   at the repo. Render reads `render.yaml` and provisions a web service
   plus a managed PostgreSQL database automatically, generating a random
   `SECRET_KEY` for you.
3. Once the first deploy finishes, open the service's **Shell** tab and run
   `flask create-admin` to create your first admin account — there is no
   public admin sign-up route.
4. Work through [PRODUCTION_CHECKLIST.md](PRODUCTION_CHECKLIST.md) before
   sharing the URL with real users.

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

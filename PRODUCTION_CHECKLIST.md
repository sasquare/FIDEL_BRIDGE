# Production Checklist

A punch list for taking FidelBridge from local development to a live
deployment on Render. Work through it top to bottom before pointing a real
domain at the app.

## 1. Secrets & configuration

- [ ] Generate a long, random `SECRET_KEY` (Render's `generateValue: true`
      in `render.yaml` does this automatically) — never reuse the
      development default. `ProductionConfig` refuses to start if it's
      still set to the dev default, so a misconfigured deploy fails loudly
      at boot instead of silently running insecurely.
- [ ] Confirm `FLASK_ENV=production` is set. This switches on secure
      cookies, HSTS, and the `SECRET_KEY` guard (see `app/config.py`).
- [ ] Confirm `DATABASE_URL` points at the managed PostgreSQL instance, not
      SQLite. `render.yaml` wires this automatically via `fromDatabase`.
- [ ] `.env` / `.flaskenv` are for local development only and are
      gitignored — nothing in them is deployed. Real config on Render comes
      entirely from dashboard/`render.yaml` environment variables.
- [ ] Set real `MAIL_SERVER`/`MAIL_PORT`/`MAIL_USERNAME`/`MAIL_PASSWORD`/
      `MAIL_DEFAULT_SENDER` env vars (a transactional email provider like
      SendGrid, Postmark, or SES's SMTP endpoint all work). Without these,
      `app/utils/mail.py` falls back to logging password-reset emails
      instead of sending them — fine for development, but it means real
      users would never receive their reset link in production.

## 2. Database

- [ ] Run `flask db upgrade` against the production database before first
      traffic (the Render build command in `render.yaml` does this on every
      deploy, which is safe — Alembic no-ops if there's nothing new to
      apply).
- [ ] Run `flask seed-categories` once the schema exists (also wired into
      the Render build command; safe to re-run).
- [ ] Create the first admin account with `flask create-admin` from a
      one-off shell against the production environment (Render dashboard
      -> service -> Shell). There is no public admin sign-up route by
      design.
- [ ] Confirm Render's managed Postgres has automatic daily backups enabled
      (on by default for paid plans; free-tier databases expire after 90
      days — upgrade before that if this is a real deployment, not a demo).

## 3. Security

- [ ] HTTPS is enforced: Render terminates TLS and provides a
      `*.onrender.com` HTTPS URL out of the box; `ProxyFix` (see
      `app/__init__.py`) makes sure Flask sees `https://` so secure
      cookies and `url_for(..., _external=True)` behave correctly.
- [ ] Security response headers (`X-Frame-Options`, `X-Content-Type-Options`,
      `Content-Security-Policy`, `Referrer-Policy`, `Strict-Transport-Security`
      in production) are applied to every response — see
      `register_security()` in `app/__init__.py`.
- [ ] Login and registration are rate-limited (`Flask-Limiter`, in-memory
      storage — fine for a single web instance; move to a Redis storage
      backend if the service ever scales to multiple instances, since
      in-memory limits don't share state across processes).
- [ ] File uploads are capped at 5&nbsp;MB, extension-allowlisted, and saved
      under random filenames (Phase 4) — verification documents are never
      served from `static/`.
- [ ] Never deploy with `DEBUG=True` — `ProductionConfig.DEBUG = False` is
      hardcoded, not environment-controlled, so this can't be flipped on by
      accident via a stray env var.

## 4. Performance

- [ ] Foreign-key and hot-filter columns are indexed (bookings by status,
      professionals by category/verification, notifications by
      user+read-state, etc. — see `PROJECT_STRUCTURE.md`).
- [ ] Static assets (`output.css`, `main.js`, vendored Alpine.js) are served
      with a 1-day `Cache-Control` and a cache-busting `?v=<mtime>` query
      string (`app/utils/assets.py`), so browsers cache aggressively without
      risking a stale asset after a deploy.
- [ ] `gunicorn` runs multiple workers in production rather than Flask's
      single-threaded dev server — tune `--workers` in the Render start
      command (`render.yaml`) based on the instance's CPU count if traffic
      grows beyond the free-tier default.

## 5. Monitoring & operations

- [ ] `/healthz` returns `200 {"status": "ok"}` and is wired as Render's
      health check path — Render restarts the instance automatically if it
      stops responding.
- [ ] Watch Render's built-in logs/metrics dashboard after the first deploy
      for 500s or slow requests.
- [ ] Consider adding an external uptime monitor (e.g. a free UptimeRobot
      check against `/healthz`) so you hear about downtime before a user
      reports it.
- [ ] No error-tracking service (e.g. Sentry) is wired up yet — the custom
      500 page shows a generic message with no stack trace to the user,
      but nothing currently captures the underlying exception anywhere
      queryable. Worth adding before relying on this for real users.

## 6. Final pre-launch pass

- [ ] Full Pytest suite passes: `pytest` (87 tests as of Phase 11).
- [ ] `npm run build` has been run **locally** and the resulting
      `app/static/css/output.css` committed, if any Tailwind classes or
      `tailwind.config.js` changed since the last deploy. Render's build
      only runs `pip install` + migrations, not `npm run build` — it
      deploys whatever compiled CSS is already checked into the repo.
- [ ] Walk through the full checklist in `INSTALLATION.md` ("Verifying the
      setup") against the live production URL, not just localhost.
- [ ] Confirm a real, non-default admin account exists and the one you used
      during development/testing (if any) is not the one guarding
      production.

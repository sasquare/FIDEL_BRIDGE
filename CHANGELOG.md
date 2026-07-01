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

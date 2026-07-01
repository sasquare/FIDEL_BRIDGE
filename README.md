# FidelBridge

**Bridging the Trust Gap.**

FidelBridge is a Nigerian trust-based service marketplace connecting
customers, verified artisans/professionals, and corporate organizations on
one platform built around verification, accountability, and quality service.

This repository is being built in phases.

- **Phase 1:** project foundation — Flask application factory, blueprint
  structure, SQLite/SQLAlchemy wiring, Tailwind CSS design system, and the
  public landing page.
- **Phase 2:** authentication — Customer/Professional/Corporate
  registration, login/logout, password hashing, role-based access control,
  and role-specific dashboard redirects.
- **Phase 3:** customer dashboard & discovery — customer profile editing,
  service categories, professional search/filtering, and public
  professional profile pages.
- **Phase 4:** professional dashboard — complete profile, skills, portfolio,
  availability, and verification document upload.
- **Phase 5:** corporate dashboard — company profile, and
  procurement / facility management / janitorial service requests.
- **Phase 6 (this phase):** booking system — hire a professional, accept/
  reject/complete jobs, and in-app notifications.

## Tech Stack

- **Backend:** Python, Flask (application factory + blueprints), SQLAlchemy, Flask-Migrate, Flask-Login, Flask-WTF
- **Frontend:** Jinja2, Tailwind CSS, Alpine.js (self-hosted, no external CDN)
- **Database:** SQLite for MVP (config supports swapping to PostgreSQL via `DATABASE_URL`)
- **Deployment target:** Render

## Project Structure

See [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) for the full breakdown.

## Getting Started

See [INSTALLATION.md](INSTALLATION.md) for full setup instructions.

Quick start:

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements-dev.txt

npm install                     # also self-hosts Alpine.js + Inter font
npm run build                   # compiles Tailwind CSS

cp .env.example .env            # then edit SECRET_KEY
flask db upgrade                # creates instance/fidelbridge.db
flask seed-categories           # populates default service categories

flask run
```

Visit http://127.0.0.1:5000 to view the landing page,
http://127.0.0.1:5000/auth/register to create an account, or
http://127.0.0.1:5000/browse/professionals to search professionals.

## Running Tests

```bash
pytest
```

## Changelog

See [CHANGELOG.md](CHANGELOG.md).

# FidelBridge

**Bridging the Trust Gap.**

FidelBridge is a Nigerian trust-based service marketplace connecting
customers, verified artisans/professionals, and corporate organizations on
one platform built around verification, accountability, and quality service.

This repository is being built in phases. **Phase 1** (this phase) delivers
the project foundation: the Flask application factory, blueprint structure,
SQLite/SQLAlchemy wiring, a Tailwind CSS design system, and the public
landing page.

## Tech Stack

- **Backend:** Python, Flask (application factory + blueprints), SQLAlchemy, Flask-Migrate
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

flask run
```

Visit http://127.0.0.1:5000 to view the landing page.

## Running Tests

```bash
pytest
```

## Changelog

See [CHANGELOG.md](CHANGELOG.md).

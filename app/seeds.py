"""Reference/lookup data seeding, run via `flask seed-categories`."""
from app.extensions import db
from app.models.category import Category
from app.utils.text import slugify

CATEGORIES = [
    ("Electricians", "M13 10V3L4 14h7v7l9-11h-7z", "Wiring, installations and electrical repairs."),
    ("Plumbers", "M9 3v2m6-2v2M5 9h14M5 9a2 2 0 00-2 2v7a2 2 0 002 2h14a2 2 0 002-2v-7a2 2 0 00-2-2M5 9l2-6h10l2 6", "Pipe fitting, leak repairs and installations."),
    ("Carpenters", "M4 6h16M4 12h16M4 18h7", "Custom furniture, fittings and woodwork."),
    ("Painters", "M12 19l7-7 3 3-7 7-3-3z M18 13l-1.5-7.5L2 2l3.5 14.5L13 18l5-5z", "Interior and exterior painting."),
    ("Cleaners", "M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z", "Home, office and post-construction cleaning."),
    ("Mechanics", "M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z", "Auto repairs, diagnostics and servicing."),
    ("Photographers", "M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z M15 13a3 3 0 11-6 0 3 3 0 016 0z", "Events, portraits and product photography."),
    ("Software Developers", "M8 9l-3 3 3 3m8-6l3 3-3 3M14 4l-4 16", "Websites, apps and custom software."),
    ("Interior Decorators", "M4 4h16v10a2 2 0 01-2 2H6a2 2 0 01-2-2V4z M8 20h8", "Space planning and interior styling."),
    ("Fashion Designers", "M9 3l3 3 3-3M6 6l-3 3 3 12h12l3-12-3-3", "Custom tailoring and fashion design."),
    ("Tutors", "M12 14l9-5-9-5-9 5 9 5z M12 14l6.16-3.42A12.02 12.02 0 0112 21a12.02 12.02 0 01-6.16-10.42L12 14z", "Private lessons and exam preparation."),
    ("Legal & Accounting", "M12 8c-3.5 0-6 1.5-6 4s2.5 4 6 4 6-1.5 6-4-2.5-4-6-4z M12 3v5m0 8v5", "Legal advice, bookkeeping and tax filing."),
]


def seed_categories():
    """Idempotently create the default service categories."""
    created = 0
    for name, icon_path, description in CATEGORIES:
        if Category.query.filter_by(name=name).first():
            continue
        db.session.add(
            Category(name=name, slug=slugify(name), icon_path=icon_path, description=description)
        )
        created += 1
    db.session.commit()
    return created

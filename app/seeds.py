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
    ("Catering", "M12 8v13m0-13V6a2 2 0 112 2h-2zm0 0V5.5A2.5 2.5 0 109.5 8H12zm-7 4h14M5 12a2 2 0 110-4h14a2 2 0 110 4M5 12v7a2 2 0 002 2h10a2 2 0 002-2v-7", "Event catering, small chops and private chefs."),
    ("Estate Developers", "M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2M5 21H3m16 0h-5v-4a1 1 0 00-1-1h-2a1 1 0 00-1 1v4H5m11-14h.01M15 7h.01M13 7h.01M11 7h.01M9 7h.01M9 11h.01M9 15h.01M13 11h.01M15 11h.01M13 15h.01M15 15h.01", "Property development, sales and management."),
    ("Event Planners", "M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z", "Weddings, parties and corporate events."),
    ("Movers & Logistics", "M9 17a2 2 0 11-4 0 2 2 0 014 0zM19 17a2 2 0 11-4 0 2 2 0 014 0z M13 16V6a1 1 0 00-1-1H4a1 1 0 00-1 1v10a1 1 0 001 1h1m8-1a1 1 0 01-1 1H9m4-1V8a1 1 0 011-1h2.586a1 1 0 01.707.293l3.414 3.414a1 1 0 01.293.707V16a1 1 0 01-1 1h-1", "Home and office relocation services."),
    ("Hair & Beauty", "M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z", "Hairdressing, makeup and grooming services."),
    ("Security Services", "M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z", "Guards, CCTV and access control."),
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

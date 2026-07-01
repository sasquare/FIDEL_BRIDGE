"""User role constants.

A plain string column (rather than a separate `Role` table or a native
SQL enum) keeps role checks simple and avoids brittle SQLite/Alembic
ALTER TYPE migrations later. Roles are fixed and few, so this is the
appropriate level of complexity for the MVP.
"""

CUSTOMER = "customer"
PROFESSIONAL = "professional"
CORPORATE = "corporate"
ADMIN = "admin"

ALL_ROLES = (CUSTOMER, PROFESSIONAL, CORPORATE, ADMIN)
REGISTERABLE_ROLES = (CUSTOMER, PROFESSIONAL, CORPORATE)

from flask import url_for

from app.models import roles

_DASHBOARD_ENDPOINTS = {
    roles.CUSTOMER: "customer.dashboard",
    roles.PROFESSIONAL: "professional.dashboard",
    roles.CORPORATE: "corporate.dashboard",
    roles.ADMIN: "main.index",  # Admin dashboard is added in Phase 9.
}


def dashboard_url_for(user):
    endpoint = _DASHBOARD_ENDPOINTS.get(user.role, "main.index")
    return url_for(endpoint)

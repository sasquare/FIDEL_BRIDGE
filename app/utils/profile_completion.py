"""Professional Profile Completion: one source of truth for both the
completion percentage (feeds Trust Score, search, Featured Professionals)
and the motivational checklist shown on the professional's dashboard.

V1 uses equal weighting deliberately - simplicity over precision until
there's real user behaviour to justify weighting some steps heavier than
others (see app/utils/trust_score.py for the equivalent reasoning on
Trust Score's weights).

Adding a future item (e.g. Insurance, Trade Licenses - see the
future-proofing list) is a single new entry in PROFILE_COMPLETION_ITEMS,
not a rewrite of anything that consumes this module.
"""
from collections import namedtuple

ChecklistItem = namedtuple("ChecklistItem", ["key", "label", "benefit", "is_complete", "edit_endpoint"])

PROFILE_COMPLETION_ITEMS = [
    (
        "profile_photo",
        "Upload a profile photo",
        "Profiles with a real photo earn more customer trust and more bookings.",
        lambda p: bool(p.profile_photo_filename),
        "professional.profile",
    ),
    (
        "bio",
        "Write a short bio",
        "Tell customers who you are and what makes you reliable.",
        lambda p: bool(p.bio and p.bio.strip()),
        "professional.profile",
    ),
    (
        "skills",
        "Add at least one skill",
        "Help customers find you for the exact service they need.",
        lambda p: len(p.skills) > 0,
        "professional.skills",
    ),
    (
        "experience",
        "Add your years of experience",
        "Experience builds customer confidence before they even message you.",
        lambda p: p.years_experience is not None,
        "professional.profile",
    ),
    (
        "service_area",
        "Set your city and state",
        "Show up when customers search for professionals in your area.",
        lambda p: bool(p.city and p.state),
        "professional.profile",
    ),
    (
        "working_hours",
        "Set your available days and hours",
        "Let customers know when you're actually available to work.",
        lambda p: bool(p.available_days and p.available_hours),
        "professional.profile",
    ),
    (
        "pricing",
        "Add your pricing information",
        "Giving customers a starting price reduces back-and-forth and wins jobs faster.",
        lambda p: bool((p.pricing_type and p.pricing_type != "not_specified") or p.consultation_fee),
        "professional.pricing",
    ),
    (
        "business_info",
        "Confirm your business type",
        "Registered businesses can display a Registered Business badge on their profile.",
        lambda p: p.professional_type == "individual" or bool(p.business_name and p.business_registration_number),
        "professional.profile",
    ),
    (
        "portfolio",
        "Add a portfolio item",
        "Show real examples of your work to win more jobs.",
        lambda p: len(p.portfolio_items) > 0,
        "professional.portfolio",
    ),
    (
        "verification",
        "Upload a verification document",
        "Verified professionals appear higher in search and win more customer trust.",
        lambda p: len(p.verifications) > 0,
        "professional.verification",
    ),
    (
        "guarantor",
        "Add guarantor information",
        "Adds an extra layer of accountability customers can trust - never shown publicly.",
        lambda p: bool(p.guarantor_name and p.guarantor_phone),
        "professional.accountability",
    ),
    (
        "emergency_contact",
        "Add an emergency contact",
        "Required for platform safety and dispute resolution - never shown publicly.",
        lambda p: bool(p.emergency_contact_name and p.emergency_contact_phone),
        "professional.accountability",
    ),
]


def profile_completion_checklist(professional):
    """Returns a list of ChecklistItem, each with whether it's already done."""
    return [
        ChecklistItem(key, label, benefit, is_complete(professional), endpoint)
        for key, label, benefit, is_complete, endpoint in PROFILE_COMPLETION_ITEMS
    ]


def profile_completion_percentage(professional):
    checklist = profile_completion_checklist(professional)
    done = sum(1 for item in checklist if item.is_complete)
    return round((done / len(checklist)) * 100)

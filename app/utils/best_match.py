"""Best Match: the composite ranking score behind the "Most Relevant"
sort on search results.

Built as a staged pipeline rather than one weighted formula - each stage
answers a different question, can be tested and tuned independently, and
can eventually be replaced (by a smarter formula, or a learned model)
without touching the others. See the Best Match design document for the
full architecture:

    Stage 0  Candidate Generation  - existing search filters (Phases 1-2)
    Stage 1  Eligibility           - hard gates (already enforced by the
                                      is_active_account filter in the
                                      candidate query)
    Stage 2  Text Relevance        - this module, text_relevance_score()
    Stage 3  Trust & Quality       - forthcoming
    Stage 4  Context Matching      - forthcoming
    Stage 5  Composite             - forthcoming

This module is built up stage by stage across several commits rather
than landing all at once, so each stage ships independently tested.
"""

# Tiered, not a flat "matches or doesn't": an exact profession match is a
# much stronger relevance signal than a keyword that merely happens to
# appear somewhere in a long bio, and the score must reflect that or
# "Most Relevant" isn't actually ranking by relevance.
RELEVANCE_EXACT_NAME = 100
RELEVANCE_EXACT_PROFESSION = 95
RELEVANCE_PROFESSION_MATCH = 80
RELEVANCE_CATEGORY_MATCH = 70
RELEVANCE_SKILL_MATCH = 60
RELEVANCE_NAME_MATCH = 50
RELEVANCE_BIO_MATCH = 30
RELEVANCE_NO_MATCH = 0


def text_relevance_score(professional, query_text, matching_category_ids=frozenset()):
    """Tiered relevance score (0-100) for how well a professional matches
    a customer's free-text search.

    matching_category_ids should be the set of Category.id values whose
    name matches query_text (computed once per search, not per
    professional - see browse/routes.py).

    professional.user and professional.skills must already be loaded
    (e.g. via selectinload) before calling this across a batch of
    professionals, or each call becomes its own extra query.
    """
    if not query_text:
        return RELEVANCE_NO_MATCH

    query_lower = query_text.strip().lower()
    if not query_lower:
        return RELEVANCE_NO_MATCH

    full_name = (professional.user.full_name or "").lower()
    profession = (professional.profession or "").lower()
    bio = (professional.bio or "").lower()

    if full_name == query_lower:
        return RELEVANCE_EXACT_NAME
    if profession == query_lower:
        return RELEVANCE_EXACT_PROFESSION
    if query_lower in profession:
        return RELEVANCE_PROFESSION_MATCH
    if professional.category_id in matching_category_ids:
        return RELEVANCE_CATEGORY_MATCH
    if any(query_lower in skill.name.lower() for skill in professional.skills):
        return RELEVANCE_SKILL_MATCH
    if query_lower in full_name:
        return RELEVANCE_NAME_MATCH
    if bio and query_lower in bio:
        return RELEVANCE_BIO_MATCH
    return RELEVANCE_NO_MATCH

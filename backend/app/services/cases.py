"""Shared case-related helpers used by both the profile (dashboard) and
cases routers, so "how do we present a Case as a CaseOut" and "how do we
match a user's stated preference to a case_type" exist exactly once.
"""
from __future__ import annotations

from app.models.case import Case, CaseType
from app.schemas.case import CaseOut

# Free-text case_preferences (e.g. "M&A", "Pricing") map onto the frozen
# CaseType taxonomy for dashboard matching (FR-04). See ARCHITECTURE.md
# ADR-06 for why this — not a firm-type -> case-type mapping — drives
# ordering, and why Product Management has no equivalent match today.
_PREFERENCE_ALIASES: dict[str, CaseType] = {
    "PROFITABILITY": CaseType.PROFITABILITY,
    "MARKET ENTRY": CaseType.MARKET_ENTRY,
    "MARKET_ENTRY": CaseType.MARKET_ENTRY,
    "M&A": CaseType.MERGERS_ACQUISITIONS,
    "MERGERS & ACQUISITIONS": CaseType.MERGERS_ACQUISITIONS,
    "MERGERS_ACQUISITIONS": CaseType.MERGERS_ACQUISITIONS,
    "PRICING": CaseType.PRICING,
    "OPERATIONS": CaseType.OPERATIONS,
    "OPS": CaseType.OPERATIONS,
}


def case_types_for_preferences(case_preferences: list[str]) -> set[CaseType]:
    matched = set()
    for pref in case_preferences:
        case_type = _PREFERENCE_ALIASES.get(pref.strip().upper())
        if case_type is not None:
            matched.add(case_type)
    return matched


def case_to_out(case: Case, viewer_id: int | None = None) -> CaseOut:
    contributor = "Anonymous" if case.owner_deleted or case.owner is None else case.owner.email.split("@")[0]
    return CaseOut(
        id=case.id,
        title=case.title,
        case_type=case.case_type,
        difficulty=case.difficulty,
        industry=case.industry,
        tags=case.tags,
        contributor=contributor,
        is_shared=case.is_shared,
        practice_count=case.practice_count,
        original_filename=case.original_filename,
        file_size_bytes=case.file_size_bytes,
        created_at=case.created_at,
        is_owner=viewer_id is not None and case.owner_id == viewer_id,
    )

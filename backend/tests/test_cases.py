"""Covers US-04 (browse/search/filter) and US-04B (upload/share) acceptance
criteria, plus ownership restrictions from FR-11.
"""
from tests.conftest import make_pdf_bytes


def _upload(client, headers, title="M&A deal case", case_type="MERGERS_ACQUISITIONS", difficulty="HARD", **kw):
    files = {"file": ("case.pdf", make_pdf_bytes(), "application/pdf")}
    data = {"title": title, "case_type": case_type, "difficulty": difficulty, **kw}
    return client.post("/cases", files=files, data=data, headers=headers)


def test_upload_rejects_non_pdf(client, signup_and_login):
    headers, _ = signup_and_login()
    files = {"file": ("case.txt", b"not a pdf", "text/plain")}
    data = {"title": "bad", "case_type": "PRICING", "difficulty": "EASY"}
    resp = client.post("/cases", files=files, data=data, headers=headers)
    assert resp.status_code == 415


def test_upload_rejects_oversized_file(client, signup_and_login, settings, monkeypatch):
    monkeypatch.setattr(settings, "max_upload_size_bytes", 100)
    headers, _ = signup_and_login()
    files = {"file": ("case.pdf", make_pdf_bytes(500), "application/pdf")}
    data = {"title": "too big", "case_type": "PRICING", "difficulty": "EASY"}
    resp = client.post("/cases", files=files, data=data, headers=headers)
    assert resp.status_code == 413


def test_upload_creates_private_case_by_default(client, signup_and_login):
    headers, _ = signup_and_login()
    resp = _upload(client, headers)
    assert resp.status_code == 201
    case = resp.json()
    assert case["is_shared"] is False
    assert case["is_owner"] is True

    # Not visible to another user under the community scope.
    other_headers, _ = signup_and_login("other@iiml.ac.in", "supersecret1")
    listing = client.get("/cases", headers=other_headers)
    assert listing.json()["total"] == 0
    assert listing.json()["is_empty"] is True


def test_is_owner_reflects_the_requesting_user_not_the_case(client, signup_and_login):
    owner_headers, _ = signup_and_login("owner@iiml.ac.in", "supersecret1")
    case_id = _upload(client, owner_headers).json()["id"]
    client.post(f"/cases/{case_id}/share", headers=owner_headers)

    other_headers, _ = signup_and_login("other@iiml.ac.in", "supersecret1")
    as_owner = client.get(f"/cases/{case_id}", headers=owner_headers).json()
    as_other = client.get(f"/cases/{case_id}", headers=other_headers).json()

    assert as_owner["is_owner"] is True
    assert as_other["is_owner"] is False


def test_share_makes_case_visible_to_others_and_withdraw_hides_it(client, signup_and_login):
    owner_headers, _ = signup_and_login("owner@iiml.ac.in", "supersecret1")
    case_id = _upload(client, owner_headers).json()["id"]

    client.post(f"/cases/{case_id}/share", headers=owner_headers)

    other_headers, _ = signup_and_login("other@iiml.ac.in", "supersecret1")
    listing = client.get("/cases", headers=other_headers)
    assert listing.json()["total"] == 1

    client.post(f"/cases/{case_id}/withdraw", headers=owner_headers)
    listing_after = client.get("/cases", headers=other_headers)
    assert listing_after.json()["total"] == 0

    # Still present in the owner's personal repository.
    mine = client.get("/cases", params={"scope": "mine"}, headers=owner_headers)
    assert mine.json()["total"] == 1


def test_filter_by_type_and_difficulty(client, signup_and_login):
    headers, _ = signup_and_login()
    id1 = _upload(client, headers, title="Hard M&A", case_type="MERGERS_ACQUISITIONS", difficulty="HARD").json()["id"]
    id2 = _upload(client, headers, title="Easy Pricing", case_type="PRICING", difficulty="EASY").json()["id"]
    for cid in (id1, id2):
        client.post(f"/cases/{cid}/share", headers=headers)

    resp = client.get("/cases", params={"case_type": "MERGERS_ACQUISITIONS", "difficulty": "HARD"}, headers=headers)
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["title"] == "Hard M&A"


def test_keyword_search_requires_three_characters(client, signup_and_login):
    headers, _ = signup_and_login()
    case_id = _upload(client, headers, title="Retail pricing deep dive").json()["id"]
    client.post(f"/cases/{case_id}/share", headers=headers)

    # A query under 3 characters is treated as "no keyword filter" rather
    # than an error (US-04 AC: "when the user types at least 3 characters").
    too_short = client.get("/cases", params={"q": "re"}, headers=headers)
    assert too_short.status_code == 200
    assert too_short.json()["total"] == 1

    matching = client.get("/cases", params={"q": "retail"}, headers=headers)
    assert matching.json()["total"] == 1

    non_matching = client.get("/cases", params={"q": "xyz123"}, headers=headers)
    assert non_matching.json()["total"] == 0


def test_empty_state_when_no_cases_match_filters(client, signup_and_login):
    headers, _ = signup_and_login()
    case_id = _upload(client, headers, case_type="PRICING").json()["id"]
    client.post(f"/cases/{case_id}/share", headers=headers)

    resp = client.get("/cases", params={"case_type": "OPERATIONS"}, headers=headers)
    body = resp.json()
    assert body["total"] == 0
    assert body["is_empty"] is True


def test_only_owner_can_edit_or_delete(client, signup_and_login):
    owner_headers, _ = signup_and_login("owner@iiml.ac.in", "supersecret1")
    case_id = _upload(client, owner_headers).json()["id"]

    other_headers, _ = signup_and_login("other@iiml.ac.in", "supersecret1")
    edit_resp = client.patch(f"/cases/{case_id}", json={"title": "hijacked"}, headers=other_headers)
    assert edit_resp.status_code == 403

    delete_resp = client.delete(f"/cases/{case_id}", headers=other_headers)
    assert delete_resp.status_code == 403


def test_non_owner_cannot_view_unshared_case(client, signup_and_login):
    owner_headers, _ = signup_and_login("owner@iiml.ac.in", "supersecret1")
    case_id = _upload(client, owner_headers).json()["id"]

    other_headers, _ = signup_and_login("other@iiml.ac.in", "supersecret1")
    resp = client.get(f"/cases/{case_id}", headers=other_headers)
    assert resp.status_code == 404


def test_practice_endpoint_increments_count_for_team1_integration(client, signup_and_login):
    headers, _ = signup_and_login()
    case_id = _upload(client, headers).json()["id"]
    client.post(f"/cases/{case_id}/share", headers=headers)

    resp = client.post(f"/cases/{case_id}/practice", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["practice_count"] == 1


def test_admin_can_moderate_shared_case(client, signup_and_login, db_session):
    from app.models.user import User

    owner_headers, _ = signup_and_login("owner@iiml.ac.in", "supersecret1")
    case_id = _upload(client, owner_headers).json()["id"]
    client.post(f"/cases/{case_id}/share", headers=owner_headers)

    admin_headers, admin_id = signup_and_login("admin@iiml.ac.in", "supersecret1")
    db_session.query(User).filter(User.id == admin_id).update({"is_admin": True})
    db_session.commit()

    non_admin_resp = client.patch(
        f"/cases/{case_id}/moderate", json={"removal_reason": "test"}, headers=owner_headers
    )
    assert non_admin_resp.status_code == 403

    admin_resp = client.patch(
        f"/cases/{case_id}/moderate", json={"removal_reason": "copyrighted material"}, headers=admin_headers
    )
    assert admin_resp.status_code == 200

    listing = client.get("/cases", params={"scope": "mine"}, headers=owner_headers)
    assert listing.json()["total"] == 0

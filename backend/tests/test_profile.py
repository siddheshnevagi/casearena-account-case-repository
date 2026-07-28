"""Covers US-03 onboarding/profile requirements (FR-03, FR-04, FR-05) and
ARCHITECTURE.md ADR-06 dashboard-ordering behavior.
"""
from tests.conftest import make_pdf_bytes


def test_onboarding_requires_authentication(client):
    resp = client.post("/profile/onboarding", json={"target_firm_type": "CONSULTING"})
    assert resp.status_code == 401


def test_onboarding_requires_mandatory_firm_type(client, signup_and_login):
    headers, _ = signup_and_login()
    resp = client.post("/profile/onboarding", json={"case_preferences": ["Pricing"]}, headers=headers)
    assert resp.status_code == 422


def test_onboarding_rejects_invalid_firm_type(client, signup_and_login):
    headers, _ = signup_and_login()
    resp = client.post(
        "/profile/onboarding", json={"target_firm_type": "ASTRONAUT"}, headers=headers
    )
    assert resp.status_code == 422


def test_onboarding_sets_profile_and_dashboard_reflects_it(client, signup_and_login):
    headers, _ = signup_and_login()
    resp = client.post(
        "/profile/onboarding",
        json={"target_firm_type": "CONSULTING", "case_preferences": ["M&A"]},
        headers=headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["target_firm_type"] == "CONSULTING"
    assert body["onboarding_completed"] is True


def test_profile_editable_after_onboarding(client, signup_and_login):
    headers, _ = signup_and_login()
    client.post("/profile/onboarding", json={"target_firm_type": "CONSULTING"}, headers=headers)

    resp = client.patch(
        "/profile/me", json={"target_firm_type": "PRODUCT_MANAGEMENT"}, headers=headers
    )
    assert resp.status_code == 200
    assert resp.json()["target_firm_type"] == "PRODUCT_MANAGEMENT"


def _upload_and_share(client, headers, title, case_type, difficulty="MEDIUM"):
    files = {"file": ("case.pdf", make_pdf_bytes(), "application/pdf")}
    data = {"title": title, "case_type": case_type, "difficulty": difficulty}
    upload = client.post("/cases", files=files, data=data, headers=headers)
    assert upload.status_code == 201, upload.text
    case_id = upload.json()["id"]
    share = client.post(f"/cases/{case_id}/share", headers=headers)
    assert share.status_code == 200
    return case_id


def test_dashboard_prioritizes_cases_matching_case_preferences(client, signup_and_login):
    contributor_headers, _ = signup_and_login("contributor@iiml.ac.in", "supersecret1")
    _upload_and_share(client, contributor_headers, "Pricing case", "PRICING")
    _upload_and_share(client, contributor_headers, "Ops case", "OPERATIONS")

    viewer_headers, _ = signup_and_login("viewer@iiml.ac.in", "supersecret1")
    client.post(
        "/profile/onboarding",
        json={"target_firm_type": "CONSULTING", "case_preferences": ["Pricing"]},
        headers=viewer_headers,
    )

    resp = client.get("/dashboard", headers=viewer_headers)
    assert resp.status_code == 200
    recommended = resp.json()["recommended_cases"]
    assert recommended[0]["case_type"] == "PRICING"


def test_dashboard_falls_back_to_newest_when_no_preference_matches(client, signup_and_login):
    contributor_headers, _ = signup_and_login("contributor@iiml.ac.in", "supersecret1")
    _upload_and_share(client, contributor_headers, "Ops case", "OPERATIONS")

    viewer_headers, _ = signup_and_login("viewer@iiml.ac.in", "supersecret1")
    client.post(
        "/profile/onboarding",
        json={"target_firm_type": "PRODUCT_MANAGEMENT", "case_preferences": []},
        headers=viewer_headers,
    )

    resp = client.get("/dashboard", headers=viewer_headers)
    assert resp.status_code == 200
    assert len(resp.json()["recommended_cases"]) == 1

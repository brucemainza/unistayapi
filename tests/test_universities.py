"""Tests for university listings."""


async def test_list_universities_returns_seed_data(client):
    response = await client.get("/api/universities")
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["status"] is True
    assert len(data["data"]) >= 5
    by_initials = {item["initials"]: item for item in data["data"]}
    assert "UNZA" in by_initials
    assert -16.0 < by_initials["UNZA"]["latitude"] < -14.0
    assert 27.0 < by_initials["UNZA"]["longitude"] < 29.0

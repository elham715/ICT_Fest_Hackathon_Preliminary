import pytest
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
import jwt

from app.main import app
from app.auth import _revoked_tokens, _revoked_refresh_tokens, JWT_SECRET, JWT_ALGORITHM
from app.database import Base, engine, SessionLocal
from app.models import Booking, Room, User, Organization, RefundLog

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_db():
    # Clear the database and recreate it for isolation
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    _revoked_tokens.clear()
    _revoked_refresh_tokens.clear()
    yield


def _future(hours: int, offset_hours: int = 0) -> str:
    tz = timezone(timedelta(hours=offset_hours)) if offset_hours else timezone.utc
    dt = datetime.now(tz) + timedelta(hours=hours)
    return dt.replace(minute=0, second=0, microsecond=0).isoformat()


def test_datetime_offset_conversion():
    # 1. Register and Login
    org = "acme"
    client.post("/auth/register", json={"org_name": org, "username": "alice", "password": "password"})
    login = client.post("/auth/login", json={"org_name": org, "username": "alice", "password": "password"}).json()
    headers = {"Authorization": f"Bearer {login['access_token']}"}

    # Create room
    room = client.post("/rooms", json={"name": "Room 1", "capacity": 5, "hourly_rate_cents": 1000}, headers=headers).json()
    room_id = room["id"]

    # Book with offset timezone (+06:00)
    # E.g., start 10 hours in future in +06:00
    start_str = _future(10, offset_hours=6)
    end_str = _future(12, offset_hours=6)
    
    resp = client.post("/bookings", json={"room_id": room_id, "start_time": start_str, "end_time": end_str}, headers=headers)
    assert resp.status_code == 201
    res_data = resp.json()
    
    # Verify return values are UTC
    assert res_data["start_time"].endswith("Z") or res_data["start_time"].endswith("+00:00")
    
    # Query from DB directly to verify conversion to UTC naive datetime
    db = SessionLocal()
    booking = db.query(Booking).filter(Booking.id == res_data["id"]).first()
    db.close()
    
    # Calculate expected UTC time
    parsed_start = datetime.fromisoformat(start_str)
    expected_utc = parsed_start.astimezone(timezone.utc).replace(tzinfo=None)
    assert booking.start_time == expected_utc


def test_booking_window_and_duration_validation():
    org = "acme"
    client.post("/auth/register", json={"org_name": org, "username": "alice", "password": "password"})
    login = client.post("/auth/login", json={"org_name": org, "username": "alice", "password": "password"}).json()
    headers = {"Authorization": f"Bearer {login['access_token']}"}

    room = client.post("/rooms", json={"name": "Room 1", "capacity": 5, "hourly_rate_cents": 1000}, headers=headers).json()
    room_id = room["id"]

    # Past start time
    past_start = (datetime.utcnow() - timedelta(minutes=10)).isoformat()
    past_end = (datetime.utcnow() + timedelta(hours=1)).isoformat()
    resp = client.post("/bookings", json={"room_id": room_id, "start_time": past_start, "end_time": past_end}, headers=headers)
    assert resp.status_code == 400
    assert resp.json()["code"] == "INVALID_BOOKING_WINDOW"

    # End before start
    start = _future(5)
    end = _future(4)
    resp = client.post("/bookings", json={"room_id": room_id, "start_time": start, "end_time": end}, headers=headers)
    assert resp.status_code == 400
    assert resp.json()["code"] == "INVALID_BOOKING_WINDOW"

    # Non-whole hours duration
    start = _future(5)
    end = (datetime.fromisoformat(start) + timedelta(minutes=90)).isoformat()
    resp = client.post("/bookings", json={"room_id": room_id, "start_time": start, "end_time": end}, headers=headers)
    assert resp.status_code == 400
    assert resp.json()["code"] == "INVALID_BOOKING_WINDOW"

    # Duration out of bounds (> 8 hours)
    start = _future(5)
    end = (datetime.fromisoformat(start) + timedelta(hours=9)).isoformat()
    resp = client.post("/bookings", json={"room_id": room_id, "start_time": start, "end_time": end}, headers=headers)
    assert resp.status_code == 400
    assert resp.json()["code"] == "INVALID_BOOKING_WINDOW"

    # Duration out of bounds (< 1 hour)
    end = start
    resp = client.post("/bookings", json={"room_id": room_id, "start_time": start, "end_time": end}, headers=headers)
    assert resp.status_code == 400
    assert resp.json()["code"] == "INVALID_BOOKING_WINDOW"


def test_back_to_back_bookings_and_overlap():
    org = "acme"
    client.post("/auth/register", json={"org_name": org, "username": "alice", "password": "password"})
    login = client.post("/auth/login", json={"org_name": org, "username": "alice", "password": "password"}).json()
    headers = {"Authorization": f"Bearer {login['access_token']}"}

    room = client.post("/rooms", json={"name": "Room 1", "capacity": 5, "hourly_rate_cents": 1000}, headers=headers).json()
    room_id = room["id"]

    # First booking 10:00 to 12:00
    b1_start = _future(10)
    b1_end = _future(12)
    resp = client.post("/bookings", json={"room_id": room_id, "start_time": b1_start, "end_time": b1_end}, headers=headers)
    assert resp.status_code == 201

    # Back-to-back starts exactly when first ends: 12:00 to 13:00 (succeeds)
    b2_start = b1_end
    b2_end = _future(13)
    resp = client.post("/bookings", json={"room_id": room_id, "start_time": b2_start, "end_time": b2_end}, headers=headers)
    assert resp.status_code == 201

    # Overlapping booking: 11:00 to 13:00 (fails 409)
    b3_start = _future(11)
    b3_end = _future(13)
    resp = client.post("/bookings", json={"room_id": room_id, "start_time": b3_start, "end_time": b3_end}, headers=headers)
    assert resp.status_code == 409
    assert resp.json()["code"] == "ROOM_CONFLICT"


def test_auth_token_exp_and_logout():
    org = "acme"
    client.post("/auth/register", json={"org_name": org, "username": "alice", "password": "password"})
    login = client.post("/auth/login", json={"org_name": org, "username": "alice", "password": "password"}).json()
    
    # 1. Check expiration claim
    payload = jwt.decode(login["access_token"], JWT_SECRET, algorithms=[JWT_ALGORITHM])
    assert payload["exp"] - payload["iat"] == 900

    # 2. Call logout and try to reuse token
    headers = {"Authorization": f"Bearer {login['access_token']}"}
    logout = client.post("/auth/logout", headers=headers)
    assert logout.status_code == 200

    # reuse token
    resp = client.get("/rooms", headers=headers)
    assert resp.status_code == 401
    assert resp.json()["code"] == "UNAUTHORIZED"


def test_refresh_token_single_use():
    org = "acme"
    client.post("/auth/register", json={"org_name": org, "username": "alice", "password": "password"})
    login = client.post("/auth/login", json={"org_name": org, "username": "alice", "password": "password"}).json()
    ref_token = login["refresh_token"]

    # first refresh succeeds
    r1 = client.post("/auth/refresh", json={"refresh_token": ref_token})
    assert r1.status_code == 200
    r1_data = r1.json()

    # second refresh with same token fails
    r2 = client.post("/auth/refresh", json={"refresh_token": ref_token})
    assert r2.status_code == 401

    # new refresh token works
    r3 = client.post("/auth/refresh", json={"refresh_token": r1_data["refresh_token"]})
    assert r3.status_code == 200


def test_tokens_require_jti_claim():
    org = "acme"
    client.post("/auth/register", json={"org_name": org, "username": "alice", "password": "password"})
    login = client.post("/auth/login", json={"org_name": org, "username": "alice", "password": "password"}).json()
    user_id = jwt.decode(login["access_token"], JWT_SECRET, algorithms=[JWT_ALGORITHM])["sub"]
    now = int(datetime.now(timezone.utc).timestamp())

    access_without_jti = jwt.encode(
        {
            "sub": user_id,
            "org": 1,
            "role": "admin",
            "iat": now,
            "exp": now + 900,
            "type": "access",
        },
        JWT_SECRET,
        algorithm=JWT_ALGORITHM,
    )
    resp = client.get("/rooms", headers={"Authorization": f"Bearer {access_without_jti}"})
    assert resp.status_code == 401
    assert resp.json()["code"] == "UNAUTHORIZED"

    refresh_without_jti = jwt.encode(
        {
            "sub": user_id,
            "org": 1,
            "role": "admin",
            "iat": now,
            "exp": now + 604800,
            "type": "refresh",
        },
        JWT_SECRET,
        algorithm=JWT_ALGORITHM,
    )
    resp = client.post("/auth/refresh", json={"refresh_token": refresh_without_jti})
    assert resp.status_code == 401
    assert resp.json()["code"] == "UNAUTHORIZED"


def test_duplicate_registration_validation():
    org = "acme"
    r1 = client.post("/auth/register", json={"org_name": org, "username": "alice", "password": "password"})
    assert r1.status_code == 201

    # Duplicate same org fails 409
    r2 = client.post("/auth/register", json={"org_name": org, "username": "alice", "password": "password"})
    assert r2.status_code == 409
    assert r2.json()["code"] == "USERNAME_TAKEN"

    # Separate org works
    r3 = client.post("/auth/register", json={"org_name": "different", "username": "alice", "password": "password"})
    assert r3.status_code == 201


def test_multi_tenancy_and_booking_visibility():
    # Org A Setup
    client.post("/auth/register", json={"org_name": "OrgA", "username": "adminA", "password": "password"})
    loginA = client.post("/auth/login", json={"org_name": "OrgA", "username": "adminA", "password": "password"}).json()
    headersA = {"Authorization": f"Bearer {loginA['access_token']}"}

    roomA = client.post("/rooms", json={"name": "Room A", "capacity": 5, "hourly_rate_cents": 1000}, headers=headersA).json()
    roomA_id = roomA["id"]

    # Org B Setup
    client.post("/auth/register", json={"org_name": "OrgB", "username": "memberB", "password": "password"})
    loginB = client.post("/auth/login", json={"org_name": "OrgB", "username": "memberB", "password": "password"}).json()
    headersB = {"Authorization": f"Bearer {loginB['access_token']}"}

    # Org B member cannot book Org A room
    resp = client.post("/bookings", json={"room_id": roomA_id, "start_time": _future(10), "end_time": _future(11)}, headers=headersB)
    assert resp.status_code == 404
    assert resp.json()["code"] == "ROOM_NOT_FOUND"

    # Org A admin creates a booking
    b_resp = client.post("/bookings", json={"room_id": roomA_id, "start_time": _future(10), "end_time": _future(11)}, headers=headersA).json()
    b_id = b_resp["id"]

    # Org B user cannot retrieve Org A booking
    g_resp = client.get(f"/bookings/{b_id}", headers=headersB)
    assert g_resp.status_code == 404
    assert g_resp.json()["code"] == "BOOKING_NOT_FOUND"

    # Org A member registration
    client.post("/auth/register", json={"org_name": "OrgA", "username": "memberA", "password": "password"})
    login_mA = client.post("/auth/login", json={"org_name": "OrgA", "username": "memberA", "password": "password"}).json()
    headers_mA = {"Authorization": f"Bearer {login_mA['access_token']}"}

    # Org A member cannot read Org A admin's booking detail
    g_resp2 = client.get(f"/bookings/{b_id}", headers=headers_mA)
    assert g_resp2.status_code == 404
    assert g_resp2.json()["code"] == "BOOKING_NOT_FOUND"


def test_admin_export_cross_org_leakage():
    # Org A Setup
    client.post("/auth/register", json={"org_name": "OrgA", "username": "adminA", "password": "password"})
    loginA = client.post("/auth/login", json={"org_name": "OrgA", "username": "adminA", "password": "password"}).json()
    headersA = {"Authorization": f"Bearer {loginA['access_token']}"}

    roomA = client.post("/rooms", json={"name": "Room A", "capacity": 5, "hourly_rate_cents": 1000}, headers=headersA).json()
    roomA_id = roomA["id"]

    # Org B Setup
    client.post("/auth/register", json={"org_name": "OrgB", "username": "adminB", "password": "password"})
    loginB = client.post("/auth/login", json={"org_name": "OrgB", "username": "adminB", "password": "password"}).json()
    headersB = {"Authorization": f"Bearer {loginB['access_token']}"}

    # Org B admin exports bookings for Org A room
    resp = client.get(f"/admin/export?include_all=true&room_id={roomA_id}", headers=headersB)
    assert resp.status_code == 404
    assert resp.json()["code"] == "ROOM_NOT_FOUND"

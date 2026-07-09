import pytest
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
import jwt

from app.main import app
from app.auth import _revoked_tokens, _revoked_refresh_tokens, JWT_SECRET, JWT_ALGORITHM
from app.services.ratelimit import _buckets
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
    _buckets.clear()
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

    # Org A member creates a booking
    b_resp3 = client.post("/bookings", json={"room_id": roomA_id, "start_time": _future(12), "end_time": _future(13)}, headers=headers_mA).json()
    b_id3 = b_resp3["id"]

    # Org A admin (adminA) CAN read Org A member's booking
    g_resp3 = client.get(f"/bookings/{b_id3}", headers=headersA)
    assert g_resp3.status_code == 200
    assert g_resp3.json()["id"] == b_id3


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


def test_rate_limiting_enforcement():
    org = "acme"
    client.post("/auth/register", json={"org_name": org, "username": "limit_user", "password": "password"})
    login = client.post("/auth/login", json={"org_name": org, "username": "limit_user", "password": "password"}).json()
    headers = {"Authorization": f"Bearer {login['access_token']}"}
    
    start = _future(10)
    end = _future(11)
    # Fire 20 requests (valid parameters so they pass Pydantic schema validation)
    for i in range(20):
        client.post("/bookings", json={"room_id": 99999, "start_time": start, "end_time": end}, headers=headers)
    
    # 21st request must be rate limited
    resp = client.post("/bookings", json={"room_id": 99999, "start_time": start, "end_time": end}, headers=headers)
    assert resp.status_code == 429
    assert resp.json()["code"] == "RATE_LIMITED"


def test_refund_notice_tiers_and_rounding():
    org = "acme"
    client.post("/auth/register", json={"org_name": org, "username": "refund_user", "password": "password"})
    login = client.post("/auth/login", json={"org_name": org, "username": "refund_user", "password": "password"}).json()
    headers = {"Authorization": f"Bearer {login['access_token']}"}
    
    # Create room with rate 1001 cents
    room = client.post("/rooms", json={"name": "Room 1", "capacity": 5, "hourly_rate_cents": 1001}, headers=headers).json()
    room_id = room["id"]
    
    # Booking starting 30 hours from now (notice 30 hours -> 50% refund)
    start_str = _future(30)
    end_str = _future(31)
    b_resp = client.post("/bookings", json={"room_id": room_id, "start_time": start_str, "end_time": end_str}, headers=headers).json()
    b_id = b_resp["id"]
    
    # Cancel it
    c_resp = client.post(f"/bookings/{b_id}/cancel", headers=headers)
    assert c_resp.status_code == 200
    c_data = c_resp.json()
    assert c_data["refund_percent"] == 50
    assert c_data["refund_amount_cents"] == 501  # round half-up: 500.5 -> 501
    
    # Retrieve and verify Refunds sub-object matches
    g_resp = client.get(f"/bookings/{b_id}", headers=headers).json()
    assert len(g_resp["refunds"]) == 1
    assert g_resp["refunds"][0]["amount_cents"] == 501


def test_cache_invalidation_flow():
    org = "acme"
    client.post("/auth/register", json={"org_name": org, "username": "cache_user", "password": "password"})
    login = client.post("/auth/login", json={"org_name": org, "username": "cache_user", "password": "password"}).json()
    headers = {"Authorization": f"Bearer {login['access_token']}"}
    
    room = client.post("/rooms", json={"name": "Room A", "capacity": 5, "hourly_rate_cents": 1000}, headers=headers).json()
    room_id = room["id"]
    
    # 1. Fetch usage report (populates cache)
    today_str = datetime.utcnow().date().isoformat()
    tomorrow_str = (datetime.utcnow() + timedelta(days=2)).date().isoformat()
    rep1 = client.get(f"/admin/usage-report?from={today_str}&to={tomorrow_str}", headers=headers).json()
    assert len(rep1["rooms"]) > 0
    room_row_1 = next(r for r in rep1["rooms"] if r["room_id"] == room_id)
    assert room_row_1["confirmed_bookings"] == 0
    
    # 2. Create booking (should invalidate report cache)
    start_str = _future(10)
    end_str = _future(11)
    b_resp = client.post("/bookings", json={"room_id": room_id, "start_time": start_str, "end_time": end_str}, headers=headers).json()
    b_id = b_resp["id"]
    
    # 3. Fetch report again (must show 1 booking immediately, not cached 0)
    rep2 = client.get(f"/admin/usage-report?from={today_str}&to={tomorrow_str}", headers=headers).json()
    room_row_2 = next(r for r in rep2["rooms"] if r["room_id"] == room_id)
    assert room_row_2["confirmed_bookings"] == 1
    
    # 4. Fetch availability (populates cache)
    avail_date = datetime.fromisoformat(start_str).date().isoformat()
    av1 = client.get(f"/rooms/{room_id}/availability?date={avail_date}", headers=headers).json()
    assert len(av1["busy"]) == 1
    
    # 5. Cancel booking (should invalidate availability cache)
    client.post(f"/bookings/{b_id}/cancel", headers=headers)
    
    # 6. Fetch availability again (must show 0 busy intervals immediately)
    av2 = client.get(f"/rooms/{room_id}/availability?date={avail_date}", headers=headers).json()
    assert len(av2["busy"]) == 0


def test_dynamic_room_stats():
    org = "acme"
    client.post("/auth/register", json={"org_name": org, "username": "stats_user", "password": "password"})
    login = client.post("/auth/login", json={"org_name": org, "username": "stats_user", "password": "password"}).json()
    headers = {"Authorization": f"Bearer {login['access_token']}"}
    
    room = client.post("/rooms", json={"name": "Room A", "capacity": 5, "hourly_rate_cents": 1000}, headers=headers).json()
    room_id = room["id"]
    
    # Stats initially 0
    st1 = client.get(f"/rooms/{room_id}/stats", headers=headers).json()
    assert st1["total_confirmed_bookings"] == 0
    assert st1["total_revenue_cents"] == 0
    
    # Create booking
    start_str = _future(10)
    end_str = _future(12) # 2 hours -> 2000 cents
    b_resp = client.post("/bookings", json={"room_id": room_id, "start_time": start_str, "end_time": end_str}, headers=headers).json()
    b_id = b_resp["id"]
    
    # Stats updated
    st2 = client.get(f"/rooms/{room_id}/stats", headers=headers).json()
    assert st2["total_confirmed_bookings"] == 1
    assert st2["total_revenue_cents"] == 2000
    
    # Cancel booking
    client.post(f"/bookings/{b_id}/cancel", headers=headers)
    
    # Stats decremented
    st3 = client.get(f"/rooms/{room_id}/stats", headers=headers).json()
    assert st3["total_confirmed_bookings"] == 0
    assert st3["total_revenue_cents"] == 0


def test_malformed_token_subject():
    import jwt
    from app.auth import JWT_SECRET, JWT_ALGORITHM
    now_ts = int(datetime.now(timezone.utc).timestamp())
    token = jwt.encode(
        {
            "sub": "non-numeric-sub",
            "org": 1,
            "role": "member",
            "jti": "somejti123",
            "iat": now_ts,
            "exp": now_ts + 900,
            "type": "access",
        },
        JWT_SECRET,
        algorithm=JWT_ALGORITHM,
    )
    resp = client.get("/rooms", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401
    assert resp.json()["code"] == "UNAUTHORIZED"


def test_booking_pagination_ordering_and_limits():
    org = "acme"
    client.post("/auth/register", json={"org_name": org, "username": "pag_user", "password": "password"})
    login = client.post("/auth/login", json={"org_name": org, "username": "pag_user", "password": "password"}).json()
    headers = {"Authorization": f"Bearer {login['access_token']}"}

    room = client.post("/rooms", json={"name": "Room 1", "capacity": 5, "hourly_rate_cents": 1000}, headers=headers).json()
    room_id = room["id"]

    # Create 5 bookings starting at different hours in the future
    # start_times: 10, 11, 12, 13, 14 hours in the future
    b_ids = []
    for h in [12, 10, 14, 11, 13]:
        resp = client.post("/bookings", json={"room_id": room_id, "start_time": _future(h), "end_time": _future(h+1)}, headers=headers).json()
        b_ids.append(resp["id"])

    # Test limit=2, page=1
    # Expected ordering: 10h, 11h, 12h, 13h, 14h
    r1 = client.get("/bookings?page=1&limit=2", headers=headers).json()
    assert r1["total"] == 5
    assert len(r1["items"]) == 2
    
    # Verify items are sorted ascending
    start_time_0 = r1["items"][0]["start_time"]
    start_time_1 = r1["items"][1]["start_time"]
    assert start_time_0 < start_time_1

    # Test limit=2, page=2 (items 3, 4)
    r2 = client.get("/bookings?page=2&limit=2", headers=headers).json()
    assert len(r2["items"]) == 2
    
    # Test limit=2, page=3 (item 5)
    r3 = client.get("/bookings?page=3&limit=2", headers=headers).json()
    assert len(r3["items"]) == 1


def test_concurrent_registration_handling():
    import concurrent.futures
    org = "concur_reg_org"
    
    # Trigger 5 parallel registrations of the same username in the same org
    def run_reg():
        return client.post("/auth/register", json={"org_name": org, "username": "same_user", "password": "password"})

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(run_reg) for _ in range(5)]
        results = [f.result() for f in futures]

    # Verify that exactly one registration returns 201 (success), and all others return 409 USERNAME_TAKEN
    success_count = sum(1 for r in results if r.status_code == 201)
    conflict_count = sum(1 for r in results if r.status_code == 409 and r.json()["code"] == "USERNAME_TAKEN")
    
    assert success_count == 1
    assert conflict_count == 4


def test_concurrent_bookings_conflict():
    import concurrent.futures
    org = "concur_book_org"
    client.post("/auth/register", json={"org_name": org, "username": "admin", "password": "password"})
    login = client.post("/auth/login", json={"org_name": org, "username": "admin", "password": "password"}).json()
    headers = {"Authorization": f"Bearer {login['access_token']}"}

    room = client.post("/rooms", json={"name": "Room 1", "capacity": 5, "hourly_rate_cents": 1000}, headers=headers).json()
    room_id = room["id"]

    start = _future(10)
    end = _future(11)

    # 5 parallel requests booking the exact same room and slot
    def run_book():
        return client.post("/bookings", json={"room_id": room_id, "start_time": start, "end_time": end}, headers=headers)

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(run_book) for _ in range(5)]
        results = [f.result() for f in futures]

    success = [r for r in results if r.status_code == 201]
    conflicts = [r for r in results if r.status_code == 409 and r.json()["code"] == "ROOM_CONFLICT"]

    assert len(success) == 1
    assert len(conflicts) == 4

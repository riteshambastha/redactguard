# Copyright 2026 Ritesh Ambastha
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
End-to-end tests for signup/login/logout and route protection

Part of RedactGuard - a self-hosted, privacy-preserving video PII redaction
toolkit with ensemble detection and a closed-loop verify-then-retry guardrail.

Author: Ritesh Ambastha
"""


def test_root_redirects_to_login_when_logged_out(client):
    r = client.get("/", follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"] == "/login"


def test_dashboard_redirects_to_login_when_logged_out(client):
    r = client.get("/dashboard", follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"] == "/login"


def test_signup_then_root_redirects_to_dashboard(client):
    client.post(
        "/signup", data={"email": "new@example.com", "password": "password123", "confirm_password": "password123"}
    )
    r = client.get("/", follow_redirects=False)
    assert r.headers["location"] == "/dashboard"


def test_signup_rejects_short_password(client):
    r = client.post("/signup", data={"email": "a@b.com", "password": "short", "confirm_password": "short"})
    assert "at least 8 characters" in r.text
    # And no session was created - still logged out.
    assert client.get("/", follow_redirects=False).headers["location"] == "/login"


def test_signup_rejects_mismatched_confirmation(client):
    r = client.post(
        "/signup", data={"email": "a@b.com", "password": "password123", "confirm_password": "somethingelse"}
    )
    assert "do not match" in r.text


def test_signup_rejects_duplicate_email(client):
    data = {"email": "dupe@example.com", "password": "password123", "confirm_password": "password123"}
    client.post("/signup", data=data)
    client.post("/logout")
    r = client.post("/signup", data=data)
    assert "already registered" in r.text


def test_login_with_correct_credentials_succeeds(signed_up_client):
    signed_up_client.post("/logout")
    r = signed_up_client.post(
        "/login", data={"email": "demo@example.com", "password": "password123"}, follow_redirects=False
    )
    assert r.headers["location"] == "/dashboard"


def test_login_with_wrong_password_fails(signed_up_client):
    signed_up_client.post("/logout")
    r = signed_up_client.post("/login", data={"email": "demo@example.com", "password": "wrong-password"})
    assert "Incorrect email or password" in r.text


def test_login_with_unknown_email_gives_the_same_error_as_wrong_password(client):
    # Deliberately the same message either way - see auth.authenticate()'s
    # docstring on not revealing which part was wrong.
    r = client.post("/login", data={"email": "nobody@example.com", "password": "whatever123"})
    assert "Incorrect email or password" in r.text


def test_logout_then_dashboard_redirects_to_login(signed_up_client):
    signed_up_client.post("/logout")
    r = signed_up_client.get("/dashboard", follow_redirects=False)
    assert r.headers["location"] == "/login"


def test_dashboard_shows_logged_in_users_email(signed_up_client):
    r = signed_up_client.get("/dashboard")
    assert "demo@example.com" in r.text


# ---------------------------------------------------------------------------
# RedactGuard - https://github.com/riteshambastha/redactguard
# Author: Ritesh Ambastha
# ---------------------------------------------------------------------------

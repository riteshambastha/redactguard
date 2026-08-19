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
Tests for the marketing landing page served at "/" for anonymous visitors

Part of RedactGuard - a self-hosted, privacy-preserving video PII redaction
toolkit with ensemble detection and a closed-loop verify-then-retry guardrail.

Author: Ritesh Ambastha

See docs/adr/0015 - "/" used to redirect straight to /login with zero
context on what the product does; this is what replaced that redirect
for anonymous visitors.
"""

from __future__ import annotations


def test_landing_page_highlights_both_sign_in_and_sign_up(client):
    r = client.get("/")
    assert r.status_code == 200
    # Both flows are rendered as prominent buttons (not just plain nav
    # links) in more than one place on the page - the hero and the
    # closing CTA banner both repeat them, per the "highlighted signup
    # and signin" ask.
    assert r.text.count('href="/signup"') >= 2
    assert r.text.count('href="/login"') >= 2
    assert "btn-primary" in r.text
    assert "Get started" in r.text
    assert "Sign in" in r.text


def test_landing_page_addresses_a_security_and_compliance_audience(client):
    r = client.get("/")
    text_lower = r.text.lower()
    for phrase in ("security", "compliance", "self-host"):
        assert phrase in text_lower, f"expected the landing page copy to mention {phrase!r}"


def test_landing_page_has_a_working_contact_us_section(client):
    r = client.get("/")
    assert "Contact" in r.text
    assert "https://github.com/riteshambastha/redactguard/issues" in r.text
    assert "https://github.com/riteshambastha/redactguard" in r.text


def test_landing_page_is_skipped_for_a_logged_in_user(signed_up_client):
    # A signed-in visitor has no use for the marketing page - straight to
    # their dashboard, unchanged from before this page existed.
    r = signed_up_client.get("/", follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"] == "/dashboard"


def test_landing_page_does_not_leak_the_authenticated_nav(client):
    # The landing page is a standalone template (not base.html) since a
    # marketing hero/section layout doesn't fit the app shell's narrow
    # centered container - this pins down that it doesn't accidentally
    # render app-only nav items (Dashboard/New job/Log out) for a visitor
    # who was never authenticated.
    r = client.get("/")
    assert "Dashboard</a>" not in r.text
    assert "Log out" not in r.text


# ---------------------------------------------------------------------------
# RedactGuard - https://github.com/riteshambastha/redactguard
# Author: Ritesh Ambastha
# ---------------------------------------------------------------------------

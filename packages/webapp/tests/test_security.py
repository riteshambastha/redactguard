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
Tests for password hashing

Part of RedactGuard - a self-hosted, privacy-preserving video PII redaction
toolkit with ensemble detection and a closed-loop verify-then-retry guardrail.

Author: Ritesh Ambastha
"""

from redactguard_webapp.security import hash_password, verify_password


def test_hash_password_is_not_the_plaintext():
    assert hash_password("correct horse") != "correct horse"


def test_verify_password_accepts_the_right_password():
    hashed = hash_password("correct horse battery staple")
    assert verify_password("correct horse battery staple", hashed) is True


def test_verify_password_rejects_the_wrong_password():
    hashed = hash_password("correct horse battery staple")
    assert verify_password("wrong password", hashed) is False


def test_verify_password_never_raises_on_a_malformed_hash():
    assert verify_password("anything", "not-a-real-bcrypt-hash") is False


def test_same_password_hashes_differently_each_time():
    # bcrypt salts each hash - two hashes of the same password must not
    # be equal, even though both verify correctly (catches an accidental
    # switch to an unsalted hash function).
    a = hash_password("correct horse battery staple")
    b = hash_password("correct horse battery staple")
    assert a != b
    assert verify_password("correct horse battery staple", a)
    assert verify_password("correct horse battery staple", b)


# ---------------------------------------------------------------------------
# RedactGuard - https://github.com/riteshambastha/redactguard
# Author: Ritesh Ambastha
# ---------------------------------------------------------------------------

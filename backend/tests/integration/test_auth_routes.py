# tests/integration/test_auth_routes.py

import pytest


class TestRegister:
    def test_register_success_returns_token_and_user(self, client):
        response = client.post(
            "/api/auth/register",
            json={"username": "amina", "email": "amina@example.com", "password": "SuperSecret123!"},
        )
        assert response.status_code == 201
        body = response.get_json()
        assert "token" in body
        assert body["user"]["username"] == "amina"
        assert body["user"]["role"] == "farmer"

    def test_defaults_to_english_when_language_omitted(self, client):
        response = client.post(
            "/api/auth/register",
            json={"username": "amina", "email": "amina@example.com", "password": "SuperSecret123!"},
        )
        assert response.get_json()["user"]["language"] == "en"

    def test_registers_with_explicit_kiswahili_preference(self, client):
        response = client.post(
            "/api/auth/register",
            json={
                "username": "fatuma",
                "email": "fatuma@example.com",
                "password": "SuperSecret123!",
                "language": "sw",
            },
        )
        assert response.get_json()["user"]["language"] == "sw"

    def test_invalid_language_returns_422(self, client):
        response = client.post(
            "/api/auth/register",
            json={
                "username": "amina",
                "email": "amina@example.com",
                "password": "SuperSecret123!",
                "language": "fr",
            },
        )
        assert response.status_code == 422

    def test_password_hash_never_appears_in_response(self, client):
        response = client.post(
            "/api/auth/register",
            json={"username": "amina", "email": "amina@example.com", "password": "SuperSecret123!"},
        )
        assert "password_hash" not in response.get_json()["user"]
        assert "password" not in response.get_json()["user"]

    def test_self_registering_as_admin_is_rejected(self, client):
        # The security fix documented in app/schemas/user_schema.py and
        # docs/TECHNICAL_DEBT.md -- this is the single most important
        # test in the whole suite, since a regression here is a
        # privilege-escalation vulnerability, not just a broken feature.
        response = client.post(
            "/api/auth/register",
            json={
                "username": "hacker",
                "email": "hacker@example.com",
                "password": "HackerPass123!",
                "role": "admin",
            },
        )
        assert response.status_code == 422
        assert "role" in response.get_json()["details"]

    def test_self_registering_as_expert_is_allowed(self, client):
        response = client.post(
            "/api/auth/register",
            json={
                "username": "expert1",
                "email": "expert1@example.com",
                "password": "SuperSecret123!",
                "role": "expert",
            },
        )
        assert response.status_code == 201
        assert response.get_json()["user"]["role"] == "expert"

    def test_duplicate_username_returns_409(self, client, amina):
        response = client.post(
            "/api/auth/register",
            json={"username": "amina", "email": "different@example.com", "password": "SuperSecret123!"},
        )
        assert response.status_code == 409

    def test_duplicate_email_returns_409(self, client, amina):
        response = client.post(
            "/api/auth/register",
            json={"username": "different", "email": "amina@example.com", "password": "SuperSecret123!"},
        )
        assert response.status_code == 409

    def test_short_password_returns_422(self, client):
        response = client.post(
            "/api/auth/register",
            json={"username": "weakpw", "email": "weak@example.com", "password": "short"},
        )
        assert response.status_code == 422

    def test_missing_fields_returns_422(self, client):
        response = client.post("/api/auth/register", json={"username": "onlyusername"})
        assert response.status_code == 422

    def test_malformed_json_body_does_not_500(self, client):
        # request.get_json(silent=True) returns None for unparseable
        # JSON rather than raising -- the route then hands `{}` to the
        # schema, which should fail validation (422), not crash the
        # server (500).
        response = client.post(
            "/api/auth/register",
            data="not valid json{{{",
            content_type="application/json",
        )
        assert response.status_code == 422


class TestLogin:
    def test_login_with_username_succeeds(self, client, amina):
        response = client.post("/api/auth/login", json={"username": "amina", "password": "TestPassword123!"})
        assert response.status_code == 200
        assert "token" in response.get_json()

    def test_login_with_email_succeeds(self, client, amina):
        response = client.post(
            "/api/auth/login", json={"email": amina["user"]["email"], "password": "TestPassword123!"}
        )
        assert response.status_code == 200

    def test_wrong_password_returns_401(self, client, amina):
        response = client.post("/api/auth/login", json={"username": "amina", "password": "wrongpassword"})
        assert response.status_code == 401

    def test_missing_password_returns_422(self, client, amina):
        response = client.post("/api/auth/login", json={"username": "amina"})
        assert response.status_code == 422


class TestMe:
    def test_no_token_returns_401(self, client):
        response = client.get("/api/auth/me")
        assert response.status_code == 401

    def test_malformed_auth_header_returns_401(self, client):
        response = client.get("/api/auth/me", headers={"Authorization": "NotBearer sometoken"})
        assert response.status_code == 401

    def test_garbage_token_returns_401(self, client):
        response = client.get("/api/auth/me", headers={"Authorization": "Bearer not.a.real.token"})
        assert response.status_code == 401

    def test_valid_token_returns_current_user(self, client, amina):
        response = client.get("/api/auth/me", headers=amina["headers"])
        assert response.status_code == 200
        assert response.get_json()["username"] == "amina"

    def test_expired_token_returns_401(self, client, amina, app):
        # Crafts a token manually with an already-past expiry, rather
        # than waiting for a real one to expire -- deliberately bypasses
        # encode_token() to control the exp claim directly.
        import jwt as pyjwt
        from datetime import datetime, timedelta, timezone

        expired_payload = {
            "sub": str(amina["user"]["id"]),
            "iat": datetime.now(timezone.utc) - timedelta(hours=2),
            "exp": datetime.now(timezone.utc) - timedelta(hours=1),
        }
        expired_token = pyjwt.encode(expired_payload, app.config["JWT_SECRET_KEY"], algorithm="HS256")

        response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {expired_token}"})
        assert response.status_code == 401
        assert "expired" in response.get_json()["error"].lower()

    def test_token_with_non_numeric_sub_returns_401(self, client, app):
        # "sub" isn't a valid user id at all -- decorators.py must catch
        # this (ValueError from int(payload["sub"])) rather than letting
        # it crash the request with an unhandled 500.
        import jwt as pyjwt

        bad_payload = {"sub": "not-a-user-id"}
        bad_token = pyjwt.encode(bad_payload, app.config["JWT_SECRET_KEY"], algorithm="HS256")

        response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {bad_token}"})
        assert response.status_code == 401

    def test_token_with_missing_sub_claim_returns_401(self, client, app):
        import jwt as pyjwt

        token_without_sub = pyjwt.encode({}, app.config["JWT_SECRET_KEY"], algorithm="HS256")

        response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token_without_sub}"})
        assert response.status_code == 401

    def test_token_for_deactivated_user_returns_401(self, client, amina):
        # The important claim in decorators.py's docstring: is_active is
        # re-checked on EVERY request, not just at login. A token issued
        # while the account was active must stop working the moment the
        # account is deactivated -- even though the token itself is
        # still validly signed and unexpired.
        from app.extensions import db
        from app.models import User

        user = db.session.get(User, amina["user"]["id"])
        user.is_active = False
        db.session.commit()

        response = client.get("/api/auth/me", headers=amina["headers"])
        assert response.status_code == 401

    def test_token_signed_with_wrong_secret_returns_401(self, client, amina):
        # Distinct from "garbage token" (which isn't even a valid JWT
        # structure) and "expired token" (correctly signed, bad exp):
        # this is a well-formed, correctly-shaped token with legitimate
        # claims, signed with a DIFFERENT secret than the app trusts.
        # This is the exact attack signature verification exists to
        # stop -- if this test ever passes with 200, the app is trusting
        # forged tokens.
        import jwt as pyjwt
        from datetime import datetime, timedelta, timezone

        forged_payload = {
            "sub": str(amina["user"]["id"]),
            "iat": datetime.now(timezone.utc),
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        }
        forged_token = pyjwt.encode(forged_payload, "attacker-controlled-secret", algorithm="HS256")

        response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {forged_token}"})
        assert response.status_code == 401


class TestForgotPassword:
    def test_known_email_returns_generic_message(self, client, amina):
        response = client.post(
            "/api/auth/forgot-password", json={"email": amina["user"]["email"]}
        )
        assert response.status_code == 200
        assert "message" in response.get_json()

    def test_unknown_email_returns_identical_generic_message(self, client):
        # Same response whether or not the email is registered --
        # otherwise this endpoint could be used to enumerate accounts.
        response = client.post(
            "/api/auth/forgot-password", json={"email": "nobody@example.com"}
        )
        assert response.status_code == 200
        assert "message" in response.get_json()

    def test_missing_email_returns_422(self, client):
        response = client.post("/api/auth/forgot-password", json={})
        assert response.status_code == 422

    def test_issues_a_usable_token(self, client, amina):
        from app.extensions import db
        from app.models import PasswordResetToken

        client.post("/api/auth/forgot-password", json={"email": amina["user"]["email"]})
        assert db.session.query(PasswordResetToken).count() == 1

    def test_actually_sends_an_email_to_the_requesting_address(self, client, amina):
        from app.extensions import mail

        with mail.record_messages() as outbox:
            response = client.post("/api/auth/forgot-password", json={"email": amina["user"]["email"]})

        assert response.status_code == 200
        assert len(outbox) == 1
        assert outbox[0].recipients == [amina["user"]["email"]]

    def test_sends_no_email_for_an_unknown_address_but_still_returns_200(self, client):
        from app.extensions import mail

        with mail.record_messages() as outbox:
            response = client.post("/api/auth/forgot-password", json={"email": "nobody@example.com"})

        assert response.status_code == 200
        assert len(outbox) == 0

    def test_response_body_never_contains_a_reset_token(self, client, amina):
        # The token/URL only ever belongs in the emailed link -- proving
        # it can't leak into the HTTP response body either.
        response = client.post("/api/auth/forgot-password", json={"email": amina["user"]["email"]})
        assert "token" not in response.get_data(as_text=True).lower()


class TestResetPassword:
    def _request_token(self, client, email):
        from app.extensions import db
        from app.models import PasswordResetToken

        client.post("/api/auth/forgot-password", json={"email": email})
        # The raw token is only ever available via the (logged) reset
        # link, never persisted -- so for the test we reach into the
        # service layer directly to mint one with a token we can assert
        # against, rather than scraping log output.
        import app.services.auth_service as auth_service

        raw_token = "test-raw-token-for-assertions"
        record = db.session.query(PasswordResetToken).first()
        record.token_hash = auth_service._hash_token(raw_token)
        db.session.commit()
        return raw_token

    def test_reset_with_valid_token_allows_login_with_new_password(self, client, amina):
        raw_token = self._request_token(client, amina["user"]["email"])

        response = client.post(
            "/api/auth/reset-password",
            json={"token": raw_token, "password": "BrandNewPassword123!"},
        )
        assert response.status_code == 200

        login_response = client.post(
            "/api/auth/login",
            json={"username": "amina", "password": "BrandNewPassword123!"},
        )
        assert login_response.status_code == 200

    def test_old_password_no_longer_works_after_reset(self, client, amina):
        raw_token = self._request_token(client, amina["user"]["email"])
        client.post(
            "/api/auth/reset-password",
            json={"token": raw_token, "password": "BrandNewPassword123!"},
        )
        response = client.post(
            "/api/auth/login", json={"username": "amina", "password": "TestPassword123!"}
        )
        assert response.status_code == 401

    def test_token_cannot_be_reused(self, client, amina):
        raw_token = self._request_token(client, amina["user"]["email"])
        client.post(
            "/api/auth/reset-password",
            json={"token": raw_token, "password": "BrandNewPassword123!"},
        )
        response = client.post(
            "/api/auth/reset-password",
            json={"token": raw_token, "password": "AnotherPassword123!"},
        )
        assert response.status_code == 422

    def test_unknown_token_returns_422(self, client):
        response = client.post(
            "/api/auth/reset-password",
            json={"token": "not-a-real-token", "password": "BrandNewPassword123!"},
        )
        assert response.status_code == 422

    def test_expired_token_returns_422(self, client, amina):
        from datetime import datetime, timedelta

        from app.extensions import db
        from app.models import PasswordResetToken
        import app.services.auth_service as auth_service

        raw_token = self._request_token(client, amina["user"]["email"])
        record = (
            db.session.query(PasswordResetToken)
            .filter_by(token_hash=auth_service._hash_token(raw_token))
            .first()
        )
        record.expires_at = datetime.utcnow() - timedelta(seconds=1)
        db.session.commit()

        response = client.post(
            "/api/auth/reset-password",
            json={"token": raw_token, "password": "BrandNewPassword123!"},
        )
        assert response.status_code == 422

    def test_short_password_returns_422(self, client, amina):
        raw_token = self._request_token(client, amina["user"]["email"])
        response = client.post(
            "/api/auth/reset-password", json={"token": raw_token, "password": "short"}
        )
        assert response.status_code == 422

    def test_missing_fields_returns_422(self, client):
        response = client.post("/api/auth/reset-password", json={})
        assert response.status_code == 422


class TestPasswordPolicy:
    """
    Exercises each individual password requirement (not just "weak
    passwords get rejected" in aggregate) against both endpoints that
    accept a new password -- registration and reset. Missing-requirement
    responses must name which requirement failed, not just fail generically.
    """

    WEAK_PASSWORDS = {
        "missing_uppercase": "lowercase123!",
        "missing_lowercase": "UPPERCASE123!",
        "missing_number": "NoNumbersHere!",
        "missing_special": "NoSpecialChar123",
        "too_short": "Sh0rt!",
    }

    @pytest.mark.parametrize("weak_password", WEAK_PASSWORDS.values(), ids=WEAK_PASSWORDS.keys())
    def test_registration_rejects_each_missing_requirement(self, client, weak_password):
        response = client.post(
            "/api/auth/register",
            json={"username": "weakpw", "email": "weak@example.com", "password": weak_password},
        )
        assert response.status_code == 422
        assert "password" in response.get_json()["details"]

    def test_registration_error_lists_every_unmet_requirement(self, client):
        # A password missing multiple requirements at once should report
        # all of them, not just the first -- so the client only needs
        # one round trip to show the user everything still missing.
        response = client.post(
            "/api/auth/register",
            json={"username": "weakpw", "email": "weak@example.com", "password": "short"},
        )
        failures = response.get_json()["details"]["password"]
        assert len(failures) > 1

    def test_registration_accepts_strong_password(self, client):
        response = client.post(
            "/api/auth/register",
            json={"username": "stronguser", "email": "strong@example.com", "password": "Str0ng!Pass"},
        )
        assert response.status_code == 201

    @pytest.mark.parametrize("weak_password", WEAK_PASSWORDS.values(), ids=WEAK_PASSWORDS.keys())
    def test_reset_password_rejects_each_missing_requirement(self, client, amina, weak_password):
        from app.extensions import db
        from app.models import PasswordResetToken
        import app.services.auth_service as auth_service

        client.post("/api/auth/forgot-password", json={"email": amina["user"]["email"]})
        raw_token = "policy-test-token"
        record = db.session.query(PasswordResetToken).first()
        record.token_hash = auth_service._hash_token(raw_token)
        db.session.commit()

        response = client.post(
            "/api/auth/reset-password", json={"token": raw_token, "password": weak_password}
        )
        assert response.status_code == 422
        assert "password" in response.get_json()["details"]


class TestChangePassword:
    def test_requires_auth(self, client):
        response = client.put(
            "/api/auth/change-password",
            json={"current_password": "TestPassword123!", "new_password": "NewStrong123!"},
        )
        assert response.status_code == 401

    def test_success_allows_login_with_new_password(self, client, amina):
        response = client.put(
            "/api/auth/change-password",
            headers=amina["headers"],
            json={"current_password": "TestPassword123!", "new_password": "NewStrong123!"},
        )
        assert response.status_code == 200

        login_response = client.post(
            "/api/auth/login", json={"username": "amina", "password": "NewStrong123!"}
        )
        assert login_response.status_code == 200

    def test_old_password_stops_working_after_change(self, client, amina):
        client.put(
            "/api/auth/change-password",
            headers=amina["headers"],
            json={"current_password": "TestPassword123!", "new_password": "NewStrong123!"},
        )
        response = client.post(
            "/api/auth/login", json={"username": "amina", "password": "TestPassword123!"}
        )
        assert response.status_code == 401

    def test_wrong_current_password_returns_401(self, client, amina):
        response = client.put(
            "/api/auth/change-password",
            headers=amina["headers"],
            json={"current_password": "WrongPassword123!", "new_password": "NewStrong123!"},
        )
        assert response.status_code == 401

    def test_weak_new_password_returns_422(self, client, amina):
        response = client.put(
            "/api/auth/change-password",
            headers=amina["headers"],
            json={"current_password": "TestPassword123!", "new_password": "weak"},
        )
        assert response.status_code == 422

    def test_missing_fields_returns_422(self, client, amina):
        response = client.put(
            "/api/auth/change-password", headers=amina["headers"], json={"current_password": "TestPassword123!"}
        )
        assert response.status_code == 422

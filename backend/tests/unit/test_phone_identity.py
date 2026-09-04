import pytest
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models.phone_identity import PhoneIdentity, normalize_phone_number


class TestNormalizePhoneNumber:
    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("+254712345678", "+254712345678"),
            ("0712345678", "+254712345678"),
            ("254712345678", "+254712345678"),
            ("00254712345678", "+254712345678"),
            ("+1 415-555-2671", "+14155552671"),
            ("  +254 712 345 678  ", "+254712345678"),
        ],
    )
    def test_normalizes_to_e164(self, raw, expected):
        assert normalize_phone_number(raw) == expected

    @pytest.mark.parametrize("raw", ["", "not a number", "+", "123"])
    def test_rejects_invalid_input(self, raw):
        with pytest.raises(ValueError):
            normalize_phone_number(raw)

    def test_none_is_rejected(self):
        with pytest.raises(ValueError):
            normalize_phone_number(None)


class TestPhoneIdentityModel:
    def test_creates_with_defaults(self, db):
        identity = PhoneIdentity(phone_number="+254712345678")
        db.session.add(identity)
        db.session.commit()

        assert identity.id is not None
        assert identity.user_id is None
        assert identity.language == "en"
        assert identity.created_at is not None
        assert identity.updated_at is not None

    def test_phone_number_must_be_unique(self, db):
        db.session.add(PhoneIdentity(phone_number="+254712345678"))
        db.session.commit()

        db.session.add(PhoneIdentity(phone_number="+254712345678"))
        with pytest.raises(IntegrityError):
            db.session.commit()

    def test_user_id_defaults_to_null_and_links_optionally(self, db, create_user):
        user = create_user(username="amina")
        identity = PhoneIdentity(phone_number="+254712345678", user_id=user.id)
        db.session.add(identity)
        db.session.commit()

        assert identity.user_id == user.id
        assert identity.user.username == "amina"

    def test_deleting_linked_user_nulls_out_the_link_not_the_row(self, db, create_user):
        user = create_user(username="amina")
        identity = PhoneIdentity(phone_number="+254712345678", user_id=user.id)
        db.session.add(identity)
        db.session.commit()
        identity_id = identity.id

        db.session.delete(user)
        db.session.commit()

        surviving = db.session.get(PhoneIdentity, identity_id)
        assert surviving is not None
        assert surviving.user_id is None

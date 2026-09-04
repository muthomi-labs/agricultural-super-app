import re
from datetime import datetime

from app.extensions import db

_KENYA_COUNTRY_CODE = "254"
_E164_PATTERN = re.compile(r"^\+[1-9]\d{6,14}$")


def normalize_phone_number(raw):
    digits = re.sub(r"[^\d+]", "", raw or "")
    if digits.startswith("+"):
        candidate = digits
    elif digits.startswith("00"):
        candidate = "+" + digits[2:]
    elif digits.startswith("0"):
        candidate = f"+{_KENYA_COUNTRY_CODE}{digits[1:]}"
    elif digits.startswith(_KENYA_COUNTRY_CODE):
        candidate = "+" + digits
    else:
        candidate = "+" + digits

    if not _E164_PATTERN.match(candidate):
        raise ValueError(f"Invalid phone number: {raw!r}")
    return candidate


class PhoneIdentity(db.Model):
    __tablename__ = "phone_identities"

    id = db.Column(db.Integer, primary_key=True)

    phone_number = db.Column(db.String(20), unique=True, nullable=False)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    language = db.Column(
        db.String(5),
        nullable=False,
        default="en",
        server_default="en",
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    user = db.relationship("User", back_populates="phone_identities")

    def __repr__(self):
        return f"<PhoneIdentity {self.phone_number}>"

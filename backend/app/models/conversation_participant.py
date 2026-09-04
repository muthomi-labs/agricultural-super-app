# app/models/conversation_participant.py

from datetime import datetime
from app.extensions import db


class ConversationParticipant(db.Model):
    __tablename__ = "conversation_participants"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    conversation_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "conversations.id",
            ondelete="CASCADE"
        ),
        nullable=False
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "users.id",
            ondelete="CASCADE"
        ),
        nullable=False,
        index=True
    )

    joined_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    conversation = db.relationship(
        "Conversation",
        back_populates="participants"
    )

    user = db.relationship(
        "User",
        back_populates="conversation_participations"
    )

    __table_args__ = (
        db.UniqueConstraint(
            "conversation_id",
            "user_id",
            name="unique_conversation_participant"
        ),
    )
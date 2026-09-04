# app/models/notification.py

from datetime import datetime
from app.extensions import db

NOTIFICATION_TYPES = ("post_like", "post_comment", "follow", "comment_reply")


class Notification(db.Model):
    __tablename__ = "notifications"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    recipient_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )

    actor_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )

    type = db.Column(
        db.String(20),
        nullable=False
    )

    post_id = db.Column(
        db.Integer,
        db.ForeignKey("posts.id", ondelete="CASCADE"),
        nullable=True
    )

    comment_id = db.Column(
        db.Integer,
        db.ForeignKey("comments.id", ondelete="CASCADE"),
        nullable=True
    )

    is_read = db.Column(
        db.Boolean,
        default=False,
        nullable=False,
        server_default="0"
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    recipient = db.relationship(
        "User",
        foreign_keys=[recipient_id],
        back_populates="notifications_received"
    )

    actor = db.relationship(
        "User",
        foreign_keys=[actor_id],
    )

    post = db.relationship("Post")

    comment = db.relationship("Comment")

    __table_args__ = (
        db.CheckConstraint(
            f"type IN {NOTIFICATION_TYPES}",
            name="ck_notifications_type"
        ),
        db.Index(
            "ix_notifications_recipient_id_is_read",
            "recipient_id",
            "is_read"
        ),
    )

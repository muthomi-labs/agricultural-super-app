# app/models/post_image.py

from datetime import datetime
from app.extensions import db


class PostImage(db.Model):
    __tablename__ = "post_images"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    post_id = db.Column(
        db.Integer,
        db.ForeignKey("posts.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    image_url = db.Column(
        db.Text,
        nullable=False
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    post = db.relationship(
        "Post",
        back_populates="images"
    )
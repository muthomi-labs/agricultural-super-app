# app/models/user.py

from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

from app.extensions import db


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)

    username = db.Column(
        db.String(50),
        unique=True,
        nullable=False
    )

    email = db.Column(
        db.String(255),
        unique=True,
        nullable=False
    )

    password_hash = db.Column(
        db.Text,
        nullable=False
    )

    role = db.Column(
        db.String(30),
        default="farmer"
    )

    is_active = db.Column(
        db.Boolean,
        default=True
    )

    # UI/AI language preference -- "en" or "sw" (Kiswahili). Drives both
    # which language the frontend renders in (see the /auth/me, login,
    # and register responses, which all dump this via UserSchema) and
    # which language the AI Farming Assistant defaults to when a
    # message's own language is ambiguous (see
    # app/services/ai_service.py's _build_system_prompt).
    language = db.Column(
        db.String(5),
        default="en",
        nullable=False,
        server_default="en",
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    # -------------------------
    # Relationships
    # -------------------------

    profile = db.relationship(
        "Profile",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan"
    )

    posts = db.relationship(
        "Post",
        back_populates="user",
        cascade="all, delete-orphan"
    )

    comments = db.relationship(
        "Comment",
        back_populates="user",
        cascade="all, delete-orphan"
    )

    likes = db.relationship(
        "Like",
        back_populates="user",
        cascade="all, delete-orphan"
    )

    created_communities = db.relationship(
        "Community",
        back_populates="creator",
        cascade="all, delete-orphan"
    )

    community_memberships = db.relationship(
        "CommunityMember",
        back_populates="user",
        cascade="all, delete-orphan"
    )

    sent_messages = db.relationship(
        "Message",
        back_populates="sender"
    )

    conversation_participations = db.relationship(
        "ConversationParticipant",
        back_populates="user",
        cascade="all, delete-orphan"
    )

    following = db.relationship(
        "UserFollow",
        foreign_keys="UserFollow.follower_id",
        back_populates="follower",
        cascade="all, delete-orphan"
    )

    followers = db.relationship(
        "UserFollow",
        foreign_keys="UserFollow.following_id",
        back_populates="following",
        cascade="all, delete-orphan"
    )

    community_follows = db.relationship(
        "CommunityFollow",
        foreign_keys="CommunityFollow.user_id",
        back_populates="follower",
        cascade="all, delete-orphan"
    )

    conversations_created = db.relationship(
        "Conversation",
        foreign_keys="Conversation.created_by",
        back_populates="creator"
    )

    ai_conversations = db.relationship(
        "AIConversation",
        back_populates="user",
        cascade="all, delete-orphan"
    )

    saved_posts = db.relationship(
        "SavedPost",
        back_populates="user",
        cascade="all, delete-orphan"
    )

    notifications_received = db.relationship(
        "Notification",
        foreign_keys="Notification.recipient_id",
        back_populates="recipient",
        cascade="all, delete-orphan"
    )

    reports_filed = db.relationship(
        "Report",
        foreign_keys="Report.reporter_id",
        back_populates="reporter",
        cascade="all, delete-orphan"
    )

    stories = db.relationship(
        "Story",
        back_populates="user",
        cascade="all, delete-orphan"
    )

    phone_identities = db.relationship(
        "PhoneIdentity",
        back_populates="user"
    )

    # -------------------------
    # Password methods
    # -------------------------

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(
            self.password_hash,
            password
        )

    def __repr__(self):
        return f"<User {self.username}>"
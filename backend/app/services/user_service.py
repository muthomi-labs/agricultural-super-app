# app/services/user_service.py

from app.errors import ConflictError, NotFoundError, ValidationAPIError
from app.extensions import db
from app.models import Profile, User, UserFollow
from app.services import notification_service

MAX_PAGE_SIZE = 100


def get_user_or_404(user_id):
    user = db.session.get(User, user_id)
    if user is None:
        raise NotFoundError(f"User {user_id} not found.")
    return user


def list_users(role=None, search=None, page=1, per_page=20):
    """
    Public user directory -- backs the Experts page (role="expert") and
    can filter to any role. `search` matches username, first name, or
    last name (case-insensitive substring), useful once profile fields
    exist without requiring a dedicated search endpoint.
    """
    per_page = min(per_page, MAX_PAGE_SIZE)
    query = db.session.query(User)

    if role:
        query = query.filter(User.role == role)

    if search:
        pattern = f"%{search}%"
        query = query.outerjoin(Profile, Profile.user_id == User.id).filter(
            db.or_(
                User.username.ilike(pattern),
                Profile.first_name.ilike(pattern),
                Profile.last_name.ilike(pattern),
            )
        )

    return (
        query.order_by(User.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )


def list_following_ids(current_user):
    rows = (
        db.session.query(UserFollow.following_id)
        .filter_by(follower_id=current_user.id)
        .all()
    )
    return [row[0] for row in rows]


def count_followers(user_id):
    get_user_or_404(user_id)
    return db.session.query(UserFollow).filter_by(following_id=user_id).count()


def upsert_own_profile(current_user, data):
    """
    Create the caller's Profile on first write, or update it on every
    write after. profiles.user_id is unique + not-null in the DBML, so a
    User has at most one Profile -- this is the only place that
    invariant is enforced at the application layer (the DB UNIQUE
    constraint enforces it as the source of truth).
    """
    profile = current_user.profile
    if profile is None:
        from app.models import Profile

        profile = Profile(user_id=current_user.id)
        db.session.add(profile)

    for key, value in data.items():
        setattr(profile, key, value)

    db.session.commit()
    return profile


def update_language(current_user, language):
    """
    Update the caller's own UI/AI language preference. `language` is
    validated by the route (see user_routes.py) against the same
    OneOf(["en", "sw"]) list UserSchema uses at registration, so both
    entry points can never disagree on what a "real" language code is.
    """
    current_user.language = language
    db.session.commit()
    return current_user


def follow_user(current_user, target_user_id):
    if current_user.id == target_user_id:
        raise ValidationAPIError("You cannot follow yourself.")

    get_user_or_404(target_user_id)  # 404 before 409: unknown target beats "already following"

    existing = (
        db.session.query(UserFollow)
        .filter_by(follower_id=current_user.id, following_id=target_user_id)
        .first()
    )
    if existing:
        raise ConflictError("You already follow this user.")

    follow = UserFollow(follower_id=current_user.id, following_id=target_user_id)
    db.session.add(follow)
    db.session.commit()
    notification_service.create_notification(
        recipient_id=target_user_id,
        actor_id=current_user.id,
        type="follow",
    )
    return follow


def unfollow_user(current_user, target_user_id):
    follow = (
        db.session.query(UserFollow)
        .filter_by(follower_id=current_user.id, following_id=target_user_id)
        .first()
    )
    if follow is None:
        raise NotFoundError("You do not follow this user.")
    db.session.delete(follow)
    db.session.commit()

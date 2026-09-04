from sqlalchemy.orm import selectinload

from app.errors import ConflictError, ForbiddenError, NotFoundError, ValidationAPIError
from app.extensions import db
from app.models import Comment, Community, Like, Post, PostImage, SavedPost
from app.models.like import REACTION_TYPES
from app.services import community_service, notification_service

_POST_LIST_EAGER_LOAD = (
    selectinload(Post.user),
    selectinload(Post.images),
    selectinload(Post.likes),
    selectinload(Post.saves),
    selectinload(Post.reposts),
    selectinload(Post.comments).selectinload(Comment.user),
    selectinload(Post.original_post).selectinload(Post.reposts),
)

MAX_PAGE_SIZE = 100


def _assert_owner(current_user, owner_id, resource_name):
    if current_user.id != owner_id and current_user.role != "admin":
        raise ForbiddenError(f"You do not have permission to modify this {resource_name}.")


def _assert_can_delete_post(current_user, post):
    if current_user.id == post.user_id or current_user.role == "admin":
        return
    if post.community_id is not None:
        community = db.session.get(Community, post.community_id)
        if community is not None and community_service.is_admin_member(current_user, community):
            return
    raise ForbiddenError("You do not have permission to delete this post.")


def _assert_can_post_in_community(current_user, community_id, is_announcement):
    community = db.session.get(Community, community_id)
    if community is None:
        raise NotFoundError(f"Community {community_id} not found.")

    if is_announcement:
        if not community_service.is_admin_member(current_user, community):
            raise ForbiddenError("Only community admins can post announcements.")
        return

    if not community_service.can_post_in_community(current_user, community):
        raise ForbiddenError("You do not have permission to post in this community.")


def get_post_or_404(post_id):
    post = db.session.get(Post, post_id)
    if post is None:
        raise NotFoundError(f"Post {post_id} not found.")
    return post


def list_posts(page=1, per_page=20, community_id=None, has_video=None):
    per_page = min(per_page, MAX_PAGE_SIZE)
    query = db.session.query(Post).filter_by(community_id=community_id).options(*_POST_LIST_EAGER_LOAD)
    if has_video:
        query = query.filter(Post.video_url.isnot(None))
    return (
        query
        .order_by(Post.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )


def increment_view_count(post_id):
    post = get_post_or_404(post_id)
    post.view_count += 1
    db.session.commit()
    return post


def list_posts_by_user(user_id, page=1, per_page=20):
    per_page = min(per_page, MAX_PAGE_SIZE)
    return (
        db.session.query(Post)
        .filter_by(user_id=user_id)
        .options(*_POST_LIST_EAGER_LOAD)
        .order_by(Post.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )


def create_post(current_user, data):
    images_data = data.pop("images", [])
    community_id = data.get("community_id")
    is_announcement = data.get("is_announcement", False)

    if community_id is not None:
        _assert_can_post_in_community(current_user, community_id, is_announcement)
    elif is_announcement:
        raise ValidationAPIError("is_announcement requires community_id.")

    post = Post(user_id=current_user.id, **data)
    db.session.add(post)
    db.session.flush()

    for image in images_data:
        db.session.add(PostImage(post_id=post.id, image_url=image["image_url"]))

    db.session.commit()
    return post


def update_post(current_user, post_id, data):
    post = get_post_or_404(post_id)
    _assert_owner(current_user, post.user_id, "post")

    data.pop("images", None)
    data.pop("community_id", None)
    data.pop("is_announcement", None)
    data.pop("video_url", None)

    for key, value in data.items():
        setattr(post, key, value)

    db.session.commit()
    return post


def delete_post(current_user, post_id):
    post = get_post_or_404(post_id)
    _assert_can_delete_post(current_user, post)
    db.session.delete(post)
    db.session.commit()


def add_post_image(current_user, post_id, image_url):
    post = get_post_or_404(post_id)
    _assert_owner(current_user, post.user_id, "post")
    image = PostImage(post_id=post.id, image_url=image_url)
    db.session.add(image)
    db.session.commit()
    return image


def delete_post_image(current_user, post_id, image_id):
    post = get_post_or_404(post_id)
    _assert_owner(current_user, post.user_id, "post")

    image = db.session.get(PostImage, image_id)
    if image is None or image.post_id != post.id:
        raise NotFoundError(f"Image {image_id} not found on post {post_id}.")

    db.session.delete(image)
    db.session.commit()


def list_comments(post_id):
    get_post_or_404(post_id)
    return (
        db.session.query(Comment)
        .filter_by(post_id=post_id)
        .order_by(Comment.created_at.asc())
        .all()
    )


def _assert_can_comment(current_user, post):
    if post.community_id is None:
        return

    community = db.session.get(Community, post.community_id)
    if community is None:
        return

    if not community.comments_enabled:
        raise ForbiddenError("Comments are closed by the community admin.")

    if not community_service.can_comment_in_community(current_user, community):
        raise ForbiddenError("You do not have permission to comment in this community.")


def add_comment(current_user, post_id, content, parent_comment_id=None):
    post = get_post_or_404(post_id)
    _assert_can_comment(current_user, post)

    parent = None
    if parent_comment_id is not None:
        parent = get_comment_or_404(parent_comment_id)
        if parent.post_id != post.id:
            raise NotFoundError(f"Comment {parent_comment_id} not found on post {post_id}.")

    comment = Comment(
        user_id=current_user.id,
        post_id=post.id,
        parent_comment_id=parent.id if parent else None,
        content=content,
    )
    db.session.add(comment)
    db.session.commit()

    if parent:
        notification_service.create_notification(
            recipient_id=parent.user_id,
            actor_id=current_user.id,
            type="comment_reply",
            post_id=post.id,
            comment_id=comment.id,
        )
    else:
        notification_service.create_notification(
            recipient_id=post.user_id,
            actor_id=current_user.id,
            type="post_comment",
            post_id=post.id,
            comment_id=comment.id,
        )
    return comment


def get_comment_or_404(comment_id):
    comment = db.session.get(Comment, comment_id)
    if comment is None:
        raise NotFoundError(f"Comment {comment_id} not found.")
    return comment


def update_comment(current_user, comment_id, content):
    comment = get_comment_or_404(comment_id)
    _assert_owner(current_user, comment.user_id, "comment")
    comment.content = content
    db.session.commit()
    return comment


def delete_comment(current_user, comment_id):
    comment = get_comment_or_404(comment_id)
    _assert_owner(current_user, comment.user_id, "comment")
    db.session.delete(comment)
    db.session.commit()


def like_post(current_user, post_id):
    post = get_post_or_404(post_id)
    existing = (
        db.session.query(Like)
        .filter_by(user_id=current_user.id, post_id=post.id)
        .first()
    )
    if existing:
        raise ConflictError("You already liked this post.")

    like = Like(user_id=current_user.id, post_id=post.id, reaction_type="like")
    db.session.add(like)
    db.session.commit()
    notification_service.create_notification(
        recipient_id=post.user_id,
        actor_id=current_user.id,
        type="post_like",
        post_id=post.id,
    )
    return like


def unlike_post(current_user, post_id):
    like = (
        db.session.query(Like)
        .filter_by(user_id=current_user.id, post_id=post_id)
        .first()
    )
    if like is None:
        raise NotFoundError("You have not liked this post.")
    db.session.delete(like)
    db.session.commit()


def set_reaction(current_user, post_id, reaction_type):
    if reaction_type not in REACTION_TYPES:
        raise ValidationAPIError(f"reaction_type must be one of: {', '.join(REACTION_TYPES)}.")

    post = get_post_or_404(post_id)
    existing = (
        db.session.query(Like)
        .filter_by(user_id=current_user.id, post_id=post.id)
        .first()
    )
    if existing:
        existing.reaction_type = reaction_type
        db.session.commit()
        return existing

    reaction = Like(user_id=current_user.id, post_id=post.id, reaction_type=reaction_type)
    db.session.add(reaction)
    db.session.commit()
    notification_service.create_notification(
        recipient_id=post.user_id,
        actor_id=current_user.id,
        type="post_like",
        post_id=post.id,
    )
    return reaction


def remove_reaction(current_user, post_id):
    reaction = (
        db.session.query(Like)
        .filter_by(user_id=current_user.id, post_id=post_id)
        .first()
    )
    if reaction is None:
        raise NotFoundError("You have not reacted to this post.")
    db.session.delete(reaction)
    db.session.commit()


def save_post(current_user, post_id):
    post = get_post_or_404(post_id)
    existing = (
        db.session.query(SavedPost)
        .filter_by(user_id=current_user.id, post_id=post.id)
        .first()
    )
    if existing:
        raise ConflictError("You already saved this post.")

    saved = SavedPost(user_id=current_user.id, post_id=post.id)
    db.session.add(saved)
    db.session.commit()
    return saved


def unsave_post(current_user, post_id):
    saved = (
        db.session.query(SavedPost)
        .filter_by(user_id=current_user.id, post_id=post_id)
        .first()
    )
    if saved is None:
        raise NotFoundError("You have not saved this post.")
    db.session.delete(saved)
    db.session.commit()


def list_saved_posts(current_user, page=1, per_page=20):
    per_page = min(per_page, MAX_PAGE_SIZE)
    return (
        db.session.query(Post)
        .join(SavedPost, SavedPost.post_id == Post.id)
        .filter(SavedPost.user_id == current_user.id)
        .options(*_POST_LIST_EAGER_LOAD)
        .order_by(SavedPost.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )


def _resolve_root_original(post):
    return post.original_post or post


def _find_repost(user_id, root_original_id):
    return (
        db.session.query(Post)
        .filter_by(user_id=user_id, original_post_id=root_original_id)
        .first()
    )


def repost_post(current_user, post_id, content=None):
    original = get_post_or_404(post_id)
    root_original = _resolve_root_original(original)

    if _find_repost(current_user.id, root_original.id):
        raise ConflictError("You have already reposted this post.")

    repost = Post(
        user_id=current_user.id,
        title=root_original.title,
        content=(content or "").strip(),
        original_post_id=root_original.id,
    )
    db.session.add(repost)
    db.session.commit()
    return repost


def unrepost_post(current_user, post_id):
    original = get_post_or_404(post_id)
    root_original = _resolve_root_original(original)

    repost = _find_repost(current_user.id, root_original.id)
    if repost is None:
        raise NotFoundError("You have not reposted this post.")

    db.session.delete(repost)
    db.session.commit()

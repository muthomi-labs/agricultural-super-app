# app/routes/user_routes.py

from flask import Blueprint, jsonify, request

from app.auth.decorators import get_current_user, jwt_required, optional_jwt
from app.errors import ValidationAPIError
from app.schemas import PostSchema, profile_schema, user_public_schema, user_schema, users_public_schema
from app.services import post_service, user_service

SUPPORTED_LANGUAGES = {"en", "sw"}

users_bp = Blueprint("users", __name__, url_prefix="/api/users")


@users_bp.get("")
def list_users():
    """
    Public user directory. `?role=expert` backs the Experts page;
    `?search=` matches username/first/last name. `?page=`, `?per_page=`
    follow the same pagination convention as posts/communities.
    ---
    tags:
      - Users
    parameters:
      - in: query
        name: role
        type: string
      - in: query
        name: search
        type: string
      - in: query
        name: page
        type: integer
        default: 1
      - in: query
        name: per_page
        type: integer
        default: 20
    responses:
      200:
        description: A page of public user profiles.
        schema:
          type: array
          items:
            $ref: '#/definitions/UserPublic'
    """
    role = request.args.get("role")
    search = request.args.get("search")
    page = request.args.get("page", default=1, type=int)
    per_page = request.args.get("per_page", default=20, type=int)
    users = user_service.list_users(role=role, search=search, page=page, per_page=per_page)
    return jsonify(users_public_schema.dump(users)), 200


@users_bp.get("/me/following")
@jwt_required
def my_following():
    """
    The set of user ids the caller currently follows.
    ---
    tags:
      - Users
    security:
      - BearerAuth: []
    responses:
      200:
        description: Ids of followed users.
        schema:
          type: object
          properties:
            following_ids:
              type: array
              items:
                type: integer
    """
    following_ids = user_service.list_following_ids(get_current_user())
    return jsonify({"following_ids": following_ids}), 200


@users_bp.get("/<int:user_id>")
def get_user(user_id):
    """
    Public profile view -- no auth required, no private fields exposed.
    ---
    tags:
      - Users
    parameters:
      - in: path
        name: user_id
        type: integer
        required: true
    responses:
      200:
        description: The user's public profile.
        schema:
          $ref: '#/definitions/UserPublic'
      404:
        description: User not found.
        schema:
          $ref: '#/definitions/Error'
    """
    user = user_service.get_user_or_404(user_id)
    return jsonify(user_public_schema.dump(user)), 200


@users_bp.get("/<int:user_id>/posts")
@optional_jwt
def get_user_posts(user_id):
    """
    List a user's posts, newest first.
    ---
    tags:
      - Users
    parameters:
      - in: path
        name: user_id
        type: integer
        required: true
      - in: query
        name: page
        type: integer
        default: 1
      - in: query
        name: per_page
        type: integer
        default: 20
    responses:
      200:
        description: A page of the user's posts.
        schema:
          type: array
          items:
            $ref: '#/definitions/Post'
      404:
        description: User not found.
        schema:
          $ref: '#/definitions/Error'
    """
    user_service.get_user_or_404(user_id)
    page = request.args.get("page", default=1, type=int)
    per_page = request.args.get("per_page", default=20, type=int)
    posts = post_service.list_posts_by_user(user_id, page=page, per_page=per_page)
    viewer = get_current_user()
    schema = PostSchema(many=True)
    schema.context = {"current_user_id": viewer.id if viewer else None}
    return jsonify(schema.dump(posts)), 200


@users_bp.get("/<int:user_id>/followers/count")
def get_followers_count(user_id):
    """
    Count a user's followers.
    ---
    tags:
      - Users
    parameters:
      - in: path
        name: user_id
        type: integer
        required: true
    responses:
      200:
        description: Follower count.
        schema:
          type: object
          properties:
            count:
              type: integer
    """
    count = user_service.count_followers(user_id)
    return jsonify({"count": count}), 200


@users_bp.put("/me/profile")
@jwt_required
def update_my_profile():
    """
    Create or update the current user's own profile.
    ---
    tags:
      - Users
    security:
      - BearerAuth: []
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            first_name:
              type: string
              x-nullable: true
            last_name:
              type: string
              x-nullable: true
            bio:
              type: string
              x-nullable: true
            location:
              type: string
              x-nullable: true
            profile_image_url:
              type: string
              x-nullable: true
            phone_number:
              type: string
              x-nullable: true
    responses:
      200:
        description: Profile saved.
        schema:
          $ref: '#/definitions/Profile'
      422:
        description: Validation failed.
        schema:
          $ref: '#/definitions/Error'
    """
    data = profile_schema.load(request.get_json(silent=True) or {}, partial=True)
    profile = user_service.upsert_own_profile(get_current_user(), data)
    return jsonify(profile_schema.dump(profile)), 200


@users_bp.put("/me/language")
@jwt_required
def update_my_language():
    """
    Update the current user's UI/AI language preference.
    ---
    tags:
      - Users
    security:
      - BearerAuth: []
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required: [language]
          properties:
            language:
              type: string
              enum: [en, sw]
    responses:
      200:
        description: Language preference saved.
        schema:
          $ref: '#/definitions/User'
      422:
        description: language must be "en" or "sw".
        schema:
          $ref: '#/definitions/Error'
    """
    payload = request.get_json(silent=True) or {}
    language = payload.get("language")
    if language not in SUPPORTED_LANGUAGES:
        raise ValidationAPIError('language must be "en" or "sw".')

    user = user_service.update_language(get_current_user(), language)
    return jsonify(user_schema.dump(user)), 200


@users_bp.post("/<int:user_id>/follow")
@jwt_required
def follow(user_id):
    """
    Follow another user.
    ---
    tags:
      - Users
    security:
      - BearerAuth: []
    parameters:
      - in: path
        name: user_id
        type: integer
        required: true
    responses:
      201:
        description: Now following.
        schema:
          type: object
          properties:
            message:
              type: string
            user_id:
              type: integer
      404:
        description: User not found.
        schema:
          $ref: '#/definitions/Error'
      409:
        description: Already following this user.
        schema:
          $ref: '#/definitions/Error'
    """
    user_service.follow_user(get_current_user(), user_id)
    return jsonify({"message": "Now following user.", "user_id": user_id}), 201


@users_bp.delete("/<int:user_id>/follow")
@jwt_required
def unfollow(user_id):
    """
    Unfollow a user.
    ---
    tags:
      - Users
    security:
      - BearerAuth: []
    parameters:
      - in: path
        name: user_id
        type: integer
        required: true
    responses:
      204:
        description: Unfollowed.
      404:
        description: Not following this user.
        schema:
          $ref: '#/definitions/Error'
    """
    user_service.unfollow_user(get_current_user(), user_id)
    return "", 204

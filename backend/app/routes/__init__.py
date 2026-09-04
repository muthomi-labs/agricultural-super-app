# app/routes/__init__.py

from .admin_routes import admin_bp
from .ai_routes import ai_bp
from .auth_routes import auth_bp
from .channel_routes import channels_bp
from .community_routes import communities_bp
from .message_routes import conversations_bp, messages_bp
from .notification_routes import notifications_bp
from .post_routes import comments_bp, posts_bp
from .story_routes import stories_bp
from .upload_routes import uploads_bp
from .user_routes import users_bp


def register_blueprints(app):
    app.register_blueprint(auth_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(posts_bp)
    app.register_blueprint(comments_bp)
    app.register_blueprint(communities_bp)
    app.register_blueprint(conversations_bp)
    app.register_blueprint(messages_bp)
    app.register_blueprint(ai_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(uploads_bp)
    app.register_blueprint(notifications_bp)
    app.register_blueprint(stories_bp)
    app.register_blueprint(channels_bp)

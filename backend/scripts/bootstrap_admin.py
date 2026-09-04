"""
One-time-use admin bootstrap: promotes a user to the admin role.

There's deliberately no self-service or API path to the admin role (see
app/schemas/user_schema.py) -- creating the very first admin is a
chicken-and-egg problem that has to be solved out-of-band once, by
someone with deploy/DB access. This script is that out-of-band path:
run it (e.g. as a one-off addition to buildCommand, or via `flask shell`)
against the target environment, then remove it from wherever it's
invoked from. Idempotent -- safe to run more than once.

Usage: python scripts/bootstrap_admin.py <username>
"""

import sys

from app import create_app
from app.extensions import db
from app.models import User


def main():
    if len(sys.argv) != 2:
        print("Usage: python scripts/bootstrap_admin.py <username>")
        sys.exit(1)

    username = sys.argv[1]
    app = create_app()
    with app.app_context():
        user = User.query.filter_by(username=username).first()
        if not user:
            print(f"BOOTSTRAP_ADMIN: no user with username={username!r}")
            sys.exit(1)
        if user.role == "admin":
            print(f"BOOTSTRAP_ADMIN: {username!r} is already admin (user_id={user.id}); no change.")
            return
        user.role = "admin"
        db.session.commit()
        print(f"BOOTSTRAP_ADMIN: promoted user_id={user.id} username={username!r} to admin.")


if __name__ == "__main__":
    main()

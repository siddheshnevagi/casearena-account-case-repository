"""Promote an existing user to admin.

There is deliberately no API endpoint for this — admin is not a
self-service role (FR-11 restricts case removal to Admin). Run this
directly against the target database when a real admin needs onboarding:

    python scripts/promote_admin.py someone@iiml.ac.in
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import SessionLocal  # noqa: E402
from app.models.user import User  # noqa: E402


def main() -> None:
    if len(sys.argv) != 2:
        print("usage: python scripts/promote_admin.py <email>")
        raise SystemExit(1)

    email = sys.argv[1]
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if user is None:
            print(f"no user found with email {email!r}")
            raise SystemExit(1)
        user.is_admin = True
        db.commit()
        print(f"{email} is now an admin")
    finally:
        db.close()


if __name__ == "__main__":
    main()

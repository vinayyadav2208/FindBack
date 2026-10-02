"""Promote a user to the ADMIN role.

Usage:
    python promote_admin.py <email>
"""

from __future__ import annotations

import sys

from app.database import SessionLocal
from app.models import User


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2

    email = sys.argv[1].strip().lower()
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if user is None:
            print(f"No user found with email '{email}'")
            return 1
        user.role = "ADMIN"
        db.commit()
        print(f"User '{user.name}' <{user.email}> is now an ADMIN")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())

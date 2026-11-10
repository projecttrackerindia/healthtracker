"""Run on the server when nobody can sign in to /admin:

    sudo docker exec -it urbanhealth python -m api.admin_cli list
    sudo docker exec -it urbanhealth python -m api.admin_cli reset admin@urbanhealth.in
    sudo docker exec -it urbanhealth python -m api.admin_cli rename OLD-EMAIL admin@urbanhealth.in

`reset` prints a new random password once, in your terminal only, and unlocks the account."""
from __future__ import annotations

import secrets
import sys

from sqlalchemy import select

from .db import SessionLocal
from .models import Admin, Audit
from .security import hash_pw


def main(argv: list[str]) -> int:
    if not argv or argv[0] not in ("list", "reset", "rename"):
        print(__doc__)
        return 2
    with SessionLocal() as db:
        if argv[0] == "list":
            for a in db.scalars(select(Admin)).all():
                print(f"{a.email:40} {a.role:8} mobile={a.phone or '-':14} locked={'yes' if (a.locked_until or 0) else 'no'}")
            return 0
        if argv[0] == "rename":
            if len(argv) < 3:
                print("usage: rename <old email> <new email>")
                return 2
            a = db.scalar(select(Admin).where(Admin.email == argv[1].strip().lower()))
            if not a:
                print("No admin with that email. Run: list")
                return 1
            new = argv[2].strip().lower()
            if "@" not in new or db.scalar(select(Admin).where(Admin.email == new)):
                print("New email is invalid or already used.")
                return 1
            db.add(Audit(who="server-console", what=f"admin.email {a.email} -> {new}"))
            a.email = new
            db.commit()
            print(f"Renamed. Sign in with {new} and the same password.")
            return 0
        if len(argv) < 2:
            print("usage: reset <email>")
            return 2
        a = db.scalar(select(Admin).where(Admin.email == argv[1].strip().lower()))
        if not a:
            print("No admin with that email. Run: list")
            return 1
        pw = "-".join(secrets.token_urlsafe(6) for _ in range(3))
        a.pw_hash, a.fails, a.locked_until = hash_pw(pw), 0, 0
        db.add(Audit(who="server-console", what=f"admin.reset {a.email}"))
        db.commit()
        print(f"\nEmail:    {a.email}\nPassword: {pw}\n\nSign in at https://urbanhealth.in/admin, then add your mobile number from the sidebar.\nThis password is shown only here; store it in a password manager.\n")
        return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

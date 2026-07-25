"""Operator CLI for the Competitors API.

Usage:
    python -m app.cli create-user --username operator --password 'Test123!'

The CLI uses the same DATABASE_URL env var as the API itself. It bypasses
the API and writes directly to the database so it can be used to bootstrap
the first user before the API is running.
"""

from __future__ import annotations

import argparse
import os
import sys
import uuid
from datetime import datetime, timezone

import bcrypt
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models import Base, User


def _env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        print(f"missing required environment variable: {name}", file=sys.stderr)
        sys.exit(2)
    return value


def _engine():
    database_url = _env("DATABASE_URL")
    connect_args = {} if database_url.startswith("postgres") else {}
    return create_engine(database_url, connect_args=connect_args)


def _ensure_schema(engine):
    """Create the tables if they don't exist. The production deployment
    uses Alembic, but in development this CLI can run before the
    migrations."""
    try:
        Base.metadata.create_all(engine)
    except Exception as exc:  # noqa: BLE001
        print(f"warning: ensure_schema failed: {exc}", file=sys.stderr)


def cmd_create_user(args: argparse.Namespace) -> int:
    engine = _engine()
    _ensure_schema(engine)
    Session = sessionmaker(bind=engine)
    with Session() as session:
        existing = session.query(User).filter(User.username == args.username).first()
        if existing:
            print(f"user {args.username!r} already exists (id={existing.id})")
            return 0
        password_hash = bcrypt.hashpw(args.password.encode(), bcrypt.gensalt(10)).decode()
        user = User(
            id=str(uuid.uuid4()),
            username=args.username,
            password_hash=password_hash,
            created_at=datetime.now(timezone.utc),
        )
        session.add(user)
        session.commit()
        print(f"created user {args.username!r} (id={user.id})")
    return 0


def cmd_list_users(args: argparse.Namespace) -> int:
    engine = _engine()
    Session = sessionmaker(bind=engine)
    with Session() as session:
        for u in session.query(User).all():
            print(f"{u.username}\t{u.id}\t{u.created_at}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Competitors API operator CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    create_user = subparsers.add_parser("create-user", help="Create a new operator user")
    create_user.add_argument("--username", required=True)
    create_user.add_argument("--password", required=True)
    create_user.set_defaults(func=cmd_create_user)

    list_users = subparsers.add_parser("list-users", help="List existing users")
    list_users.set_defaults(func=cmd_list_users)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

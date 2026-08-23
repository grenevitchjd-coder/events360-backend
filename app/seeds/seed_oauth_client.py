"""
Registers a downstream app (EventNXT, etc.) as an OAuth2 client, so it can
offer "Sign in with Events360." Prints the generated client_secret ONCE —
copy it immediately, it's stored hashed and can't be retrieved again.

Run via environment variables (safer than hardcoding in this file):
    OAUTH_CLIENT_ID=eventnxt \
    OAUTH_CLIENT_NAME="EventNXT" \
    OAUTH_REDIRECT_URIS="https://eventnxt-backend.herokuapp.com/auth/callback" \
    python -m app.seeds.seed_oauth_client

Safe to re-run for a DIFFERENT client_id — skips (does not overwrite) an
existing one, so re-running never silently invalidates a live secret.
"""

import os
import secrets
import sys

from app.database import SessionLocal
from app.models.oauth_client import OAuthClient
from app.services.security import hash_password


def run():
    client_id = os.environ.get("OAUTH_CLIENT_ID")
    name = os.environ.get("OAUTH_CLIENT_NAME")
    redirect_uris = os.environ.get("OAUTH_REDIRECT_URIS")

    if not all([client_id, name, redirect_uris]):
        print(
            "Missing OAUTH_CLIENT_ID / OAUTH_CLIENT_NAME / OAUTH_REDIRECT_URIS "
            "environment variables. Aborting.",
            file=sys.stderr,
        )
        sys.exit(1)

    db = SessionLocal()
    try:
        existing = db.query(OAuthClient).filter(OAuthClient.client_id == client_id).first()
        if existing:
            print(f"A client with client_id '{client_id}' already exists. Skipping (secret unchanged).")
            return

        client_secret = secrets.token_urlsafe(32)
        client = OAuthClient(
            client_id=client_id,
            client_secret_hash=hash_password(client_secret),
            name=name,
            redirect_uris=redirect_uris,
        )
        db.add(client)
        db.commit()

        print(f"Registered OAuth client '{client_id}'.")
        print("")
        print("client_id:     " + client_id)
        print("client_secret: " + client_secret)
        print("")
        print("Copy the client_secret now — it's stored hashed and cannot be shown again.")
        print("Set these as OAUTH_CLIENT_ID / OAUTH_CLIENT_SECRET config vars on the downstream app.")
    finally:
        db.close()


if __name__ == "__main__":
    run()
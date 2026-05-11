"""Provision Vapi assistants for any clinic that doesn't have one yet.

Idempotent. Run after onboarding a new pilot clinic (or let the
autoresume cron run it). Once each clinic has a vapi_assistant_id,
this script is a no-op.

    python scripts/provision_pending_assistants.py
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db import supabase_admin  # noqa: E402
from services.vapi_provision import create_assistant_for_clinic  # noqa: E402


def main() -> None:
    client = supabase_admin()
    pending = (
        client.table("clinics")
        .select("id,name")
        .is_("vapi_assistant_id", "null")
        .execute()
    ).data or []
    if not pending:
        print("No clinics pending Vapi assistant provisioning.")
        return
    print(f"Provisioning {len(pending)} assistant(s)...")
    for c in pending:
        try:
            assistant_id = create_assistant_for_clinic(c["id"])
            print(f"  {c['name']}: {assistant_id}")
        except Exception as exc:
            print(f"  {c['name']}: FAILED — {exc}")


if __name__ == "__main__":
    main()

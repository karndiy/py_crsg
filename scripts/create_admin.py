"""Set the dashboard admin credentials.

Admin auth is env-var based (ADMIN_USERNAME / ADMIN_PASSWORD in .env)
-- there is no admin-users table in this system's design. This script
only writes/updates those two values in a .env file; it does not touch
the database.
"""

from __future__ import annotations

import getpass
import sys
from pathlib import Path

ENV_PATH = Path(".env")


def set_env_value(key: str, value: str) -> None:
    lines = ENV_PATH.read_text(encoding="utf-8").splitlines() if ENV_PATH.exists() else []
    found = False
    for i, line in enumerate(lines):
        if line.startswith(f"{key}="):
            lines[i] = f"{key}={value}"
            found = True
            break
    if not found:
        lines.append(f"{key}={value}")
    ENV_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    username = input("Admin username: ").strip() or "admin"
    password = getpass.getpass("Admin password: ").strip()
    if not password:
        print("Password cannot be empty.")
        sys.exit(1)

    set_env_value("ADMIN_USERNAME", username)
    set_env_value("ADMIN_PASSWORD", password)
    print(f"Updated {ENV_PATH} -- restart community-radio.service for this to take effect.")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Vibe Web Terminal — User Management CLI

Manage local users in auth.yaml. Passwords are stored as bcrypt hashes
with random per-user salt (12 rounds).

Usage:
    python3 edit_user.py list                  List all users
    python3 edit_user.py add <username>        Add a user (prompts for password)
    python3 edit_user.py remove <username>     Remove a user
    python3 edit_user.py passwd <username>     Change a user's password

If auth.yaml does not exist, it is created from auth.yaml.example.
"""

import argparse
import getpass
import shutil
import sys
from datetime import datetime
from pathlib import Path

import bcrypt
import yaml

CONFIG_PATH = Path(__file__).parent / "auth.yaml"
EXAMPLE_PATH = Path(__file__).parent / "auth.yaml.example"


def load_config() -> dict:
    """Load auth.yaml, creating it from the example if needed."""
    if not CONFIG_PATH.exists():
        if not EXAMPLE_PATH.exists():
            print(f"Error: Neither {CONFIG_PATH} nor {EXAMPLE_PATH} found.")
            print("Re-clone the repository or create auth.yaml manually.")
            sys.exit(1)
        print(f"Creating {CONFIG_PATH} from {EXAMPLE_PATH} ...")
        shutil.copy2(EXAMPLE_PATH, CONFIG_PATH)

    with open(CONFIG_PATH) as f:
        config = yaml.safe_load(f) or {}

    # Ensure users dict exists
    if "users" not in config or config["users"] is None:
        config["users"] = {}

    return config


def save_config(config: dict) -> None:
    """Write config back to auth.yaml preserving readability."""
    with open(CONFIG_PATH, "w") as f:
        yaml.dump(
            config, f,
            default_flow_style=False,
            sort_keys=False,
            allow_unicode=True,
            width=120,
        )


def prompt_password(confirm: bool = True) -> str:
    """Prompt for a password with optional confirmation."""
    while True:
        password = getpass.getpass("Password: ")
        if len(password) < 4:
            print("Password must be at least 4 characters.")
            continue
        if confirm:
            password2 = getpass.getpass("Confirm password: ")
            if password != password2:
                print("Passwords do not match. Try again.")
                continue
        return password


def hash_password(password: str) -> str:
    """Hash a password with bcrypt (random salt, 12 rounds)."""
    return bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt(rounds=12),
    ).decode("utf-8")


# =========================================================================
# Subcommands
# =========================================================================

def cmd_list(args: argparse.Namespace) -> None:
    """List all local users."""
    config = load_config()
    users = config.get("users") or {}

    if not users:
        print("No local users configured.")
        print(f"Add one with: python3 {Path(__file__).name} add <username>")
        return

    print(f"{'Username':<20} {'Created'}")
    print("-" * 45)
    for name, info in sorted(users.items()):
        created = info.get("created_at", "unknown")
        print(f"{name:<20} {created}")
    print(f"\n{len(users)} user(s) total.")


def cmd_add(args: argparse.Namespace) -> None:
    """Add a new user."""
    config = load_config()
    users = config.get("users", {})

    username = args.username
    if username in users:
        print(f"Error: User '{username}' already exists.")
        print(f"Use 'passwd' to change their password, or 'remove' first.")
        sys.exit(1)

    print(f"Adding user '{username}'.")
    password = prompt_password()

    users[username] = {
        "password_hash": hash_password(password),
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }
    config["users"] = users
    save_config(config)
    print(f"User '{username}' added successfully.")


def cmd_remove(args: argparse.Namespace) -> None:
    """Remove a user."""
    config = load_config()
    users = config.get("users", {})

    username = args.username
    if username not in users:
        print(f"Error: User '{username}' not found.")
        sys.exit(1)

    confirm = input(f"Remove user '{username}'? [y/N]: ").strip().lower()
    if confirm != "y":
        print("Cancelled.")
        return

    del users[username]
    config["users"] = users
    save_config(config)
    print(f"User '{username}' removed.")


def cmd_passwd(args: argparse.Namespace) -> None:
    """Change a user's password."""
    config = load_config()
    users = config.get("users", {})

    username = args.username
    if username not in users:
        print(f"Error: User '{username}' not found.")
        sys.exit(1)

    print(f"Changing password for '{username}'.")
    password = prompt_password()

    users[username]["password_hash"] = hash_password(password)
    config["users"] = users
    save_config(config)
    print(f"Password updated for '{username}'.")


# =========================================================================
# Main
# =========================================================================

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Manage Vibe Web Terminal local users.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python3 edit_user.py add admin        Add an admin user\n"
            "  python3 edit_user.py list              Show all users\n"
            "  python3 edit_user.py passwd admin      Change admin password\n"
            "  python3 edit_user.py remove olduser    Delete a user\n"
        ),
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # list
    sp_list = subparsers.add_parser("list", help="List all users")
    sp_list.set_defaults(func=cmd_list)

    # add
    sp_add = subparsers.add_parser("add", help="Add a new user")
    sp_add.add_argument("username", help="Username to add")
    sp_add.set_defaults(func=cmd_add)

    # remove
    sp_rm = subparsers.add_parser("remove", help="Remove a user")
    sp_rm.add_argument("username", help="Username to remove")
    sp_rm.set_defaults(func=cmd_remove)

    # passwd
    sp_pw = subparsers.add_parser("passwd", help="Change a user's password")
    sp_pw.add_argument("username", help="Username to update")
    sp_pw.set_defaults(func=cmd_passwd)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()

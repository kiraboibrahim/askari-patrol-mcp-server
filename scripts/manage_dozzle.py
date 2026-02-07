"""
Dozzle User Management Script

This script manages user authentication for Dozzle (a Docker log viewer) by generating
password hashes and maintaining a YAML configuration file.

Usage:
    python manage_dozzle.py <username> <password> [email] [name]

Arguments:
    username    : The username for the Dozzle user (required)
    password    : The password for the user (required)
    email       : Email address (optional, defaults to <username>@example.com)
    name        : Display name (optional, defaults to capitalized username)

Examples:
    # Create user with defaults
    python manage_dozzle.py alice mySecureP@ss

    # Create user with custom email
    python manage_dozzle.py bob p@ssw0rd bob.smith@company.com

    # Create user with full details
    python manage_dozzle.py charlie pass123 charlie@email.com "Charlie Brown"

Output:
    Creates or updates 'dozzle_users.yml' with the user configuration including
    the hashed password and other user details.

Requirements:
    - Docker must be installed and running
    - PyYAML package: pip install pyyaml
    - Internet access to pull amir20/dozzle image (first run only)
"""

import subprocess
import sys
from pathlib import Path

import yaml


def generate_dozzle_user(username, password, email=None, name=None):
    """
    Generate a Dozzle user configuration with hashed password.

    Uses the official Dozzle Docker image to generate a secure password hash
    and user configuration block.

    Args:
        username (str): Username for the Dozzle account
        password (str): Plain-text password (will be hashed by Dozzle)
        email (str, optional): User's email address
        name (str, optional): User's display name

    Returns:
        dict: User configuration dictionary containing hashed password and metadata

    Raises:
        SystemExit: If Docker command fails or Dozzle image is unavailable

    Example:
        >>> data = generate_dozzle_user('alice', 'secret123', 'alice@example.com')
        >>> print(data.keys())
        dict_keys(['password', 'email', 'name'])
    """
    cmd = [
        "docker",
        "run",
        "--rm",
        "amir20/dozzle",
        "generate",
        username,
        "--password",
        password,
    ]

    if email:
        cmd.extend(["--email", email])
    if name:
        cmd.extend(["--name", name])

    try:
        print(f"Generating hash for user '{username}'...")
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)

        # The output is a YAML block starting with 'users:'
        output_yaml = yaml.safe_load(result.stdout)
        user_data = output_yaml["users"][username]
        return user_data

    except subprocess.CalledProcessError as e:
        print(f"Error calling Docker: {e}")
        print(f"stderr: {e.stderr}")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)


def update_users_file(username, user_data):
    """
    Update or create the Dozzle users configuration file.

    Adds or updates a user in 'dozzle_users.yml'. If the file doesn't exist,
    it will be created. If the user already exists, their configuration will
    be updated.

    Args:
        username (str): Username to add/update
        user_data (dict): User configuration data (from generate_dozzle_user)

    Side Effects:
        Creates or modifies 'dozzle_users.yml' in the current directory

    Example:
        >>> user_data = {'password': '$2a$10$...', 'email': 'alice@example.com'}
        >>> update_users_file('alice', user_data)
        Successfully updated 'alice' in dozzle_users.yml
    """
    file_path = Path("dozzle_users.yml")

    # Load existing config or create new one
    if file_path.exists():
        with open(file_path) as f:
            full_config = yaml.safe_load(f) or {}
    else:
        full_config = {}

    # Ensure 'users' key exists
    if "users" not in full_config:
        full_config["users"] = {}

    # Add or update user
    full_config["users"][username] = user_data

    # Write back to file
    with open(file_path, "w") as f:
        yaml.dump(full_config, f, default_flow_style=False, sort_keys=False)

    print(f"Successfully updated '{username}' in dozzle_users.yml")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python manage_dozzle.py <username> <password> [email] [name]")
        print("\nExamples:")
        print("  python manage_dozzle.py alice myP@ssw0rd")
        print("  python manage_dozzle.py bob secret bob@company.com")
        print(
            "  python manage_dozzle.py charlie pass123 charlie@email.com 'Charlie Brown'"
        )
        sys.exit(1)

    # Parse command-line arguments
    user = sys.argv[1]
    pwd = sys.argv[2]
    mail = sys.argv[3] if len(sys.argv) > 3 else f"{user}@example.com"
    display_name = sys.argv[4] if len(sys.argv) > 4 else user.capitalize()

    # Generate and save user configuration
    data = generate_dozzle_user(user, pwd, mail, display_name)
    update_users_file(user, data)

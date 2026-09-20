"""Write the .env file to upload to Vercel, complete and ready.

    python -m app.vercel_env --ref <project ref>

Asks for the Supabase database password (hidden), works out the Transaction pooler address, and writes
`.env.vercel` with a signing key. Import that file in Vercel under Settings > Environment Variables.
The file is git-ignored. Delete it once Vercel has the values.
"""

import argparse
import getpass
import secrets
import sys
from pathlib import Path
from urllib.parse import quote

from app.supabase_load import find_pooler

TEMPLATE = """# Environment variables for the Vantage API project on Vercel. Never commit this file.
# In Vercel: Settings > Environment Variables > Import .env

DATABASE_URL={database_url}
VANTAGE_SECRET={secret}
VANTAGE_SKIP_DDL=1
VANTAGE_SCHEDULER=0
"""


def transaction_url(ref: str, host: str, password: str) -> str:
    """The Transaction pooler string (port 6543), which is the one serverless functions should use."""
    return f"postgresql://postgres.{ref}:{quote(password, safe='')}@{host}:6543/postgres"


def existing_secret(path: Path) -> str | None:
    """Keep the same signing key if the file already has one, so people stay logged in across deploys."""
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.startswith("VANTAGE_SECRET=") and len(line) > len("VANTAGE_SECRET=") + 16:
                return line.split("=", 1)[1].strip()
    return None


def main(argv: list[str]) -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--ref", required=True, help="your project ref, the part before .supabase.co")
    parser.add_argument("--host", help="pooler host, if you already know it (otherwise it is looked up)")
    parser.add_argument("--out", default=".env.vercel", help="file to write")
    args = parser.parse_args(argv)

    host = args.host or find_pooler(args.ref)
    if not host:
        raise SystemExit("Could not find that project's pooler. Check the project ref, and that the project is not paused.")
    password = getpass.getpass("Supabase database password (hidden): ")
    if not password:
        raise SystemExit("No password given.")

    out = Path(args.out)
    secret = existing_secret(out) or secrets.token_hex(32)
    out.write_text(TEMPLATE.format(database_url=transaction_url(args.ref, host, password), secret=secret), encoding="utf-8")
    print(f"Wrote {out.resolve()}")
    print("In Vercel: Settings > Environment Variables > Import .env, choose that file, then Redeploy.")


if __name__ == "__main__":
    main(sys.argv[1:])

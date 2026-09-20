"""One command to load Vantage's data into a Supabase project.

    python -m app.supabase_load --ref <project ref>

It asks for the database password (nothing is shown as you type), finds which pooler region your
project lives in, creates the tables, switches on row level security and copies the data. It saves
you from hand-building a connection string. Nothing is stored.
"""

import argparse
import getpass
import sys
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import quote

import psycopg

REGIONS = [
    "ap-south-1", "ap-southeast-1", "ap-southeast-2", "ap-northeast-1", "ap-northeast-2", "ap-northeast-3",
    "us-east-1", "us-east-2", "us-west-1", "us-west-2", "ca-central-1",
    "eu-west-1", "eu-west-2", "eu-west-3", "eu-central-1", "eu-central-2", "eu-north-1",
    "sa-east-1", "me-central-1", "il-central-1", "af-south-1",
]
PREFIXES = ("aws-0", "aws-1")


def classify(message: str) -> str:
    """What a failed connection tells us: wrong region, right region with a refused password, or something else."""
    text = message.lower()
    if "password authentication failed" in text or "authentication failed" in text:
        return "right-region"
    if "tenant/user" in text or "tenant or user not found" in text or "enotfound" in text:
        return "wrong-region"
    return "other"


def try_host(host: str, ref: str, password: str, connect=psycopg.connect, timeout: int = 8) -> tuple[str, str]:
    try:
        with connect(host=host, port=5432, user=f"postgres.{ref}", password=password, dbname="postgres", connect_timeout=timeout):
            return host, "ok"
    except psycopg.Error as exc:
        return host, classify(str(exc))
    except OSError as exc:
        return host, f"other:{exc}"


def find_pooler(ref: str, connect=psycopg.connect) -> str | None:
    """Which pooler host serves this project. Asks every region with a throwaway password: only the
    project's own region answers "password authentication failed", the rest say they don't know the project.
    Your real password is never sent to a region that isn't yours."""
    hosts = [f"{p}-{r}.pooler.supabase.com" for p in PREFIXES for r in REGIONS]
    with ThreadPoolExecutor(max_workers=12) as pool:
        for host, status in pool.map(lambda h: try_host(h, ref, "not-the-real-password", connect), hosts):
            if status == "right-region":
                return host
    return None


def main(argv: list[str]) -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--ref", required=True, help="your project ref, the part before .supabase.co")
    parser.add_argument("--replace", action="store_true", help="empty the tables in Supabase first")
    args = parser.parse_args(argv)

    print("Looking for your project's region ...")
    host = find_pooler(args.ref)
    if host is None:
        raise SystemExit(
            "No Supabase pooler recognised that project ref. Check the ref (the part before .supabase.co) "
            "and that the project is not paused."
        )
    print(f"Found it: {host}")

    password = getpass.getpass("Supabase database password (hidden): ")
    print("Checking the password (this can take a few seconds) ...")
    _, status = try_host(host, args.ref, password, timeout=45)
    if status != "ok":
        hint = "the password was refused. Check it, or reset it in Supabase." if status == "right-region" else f"the connection failed ({status})."
        raise SystemExit(f"Found your project at {host}, but {hint}")

    session_url = f"postgresql://postgres.{args.ref}:{quote(password, safe='')}@{host}:5432/postgres"
    from app import copy_db
    from app.migrate import add_missing_columns
    from sqlalchemy import create_engine

    from app.db import engine_options, normalize_url

    url = normalize_url(session_url)
    add_missing_columns(create_engine(url, **engine_options(url, False)))
    copy_db.main(["--to", session_url, *(["--replace"] if args.replace else [])])

    print("\nFor Vercel and GitHub, use the Transaction pooler string. It is the same but with port 6543:")
    print(f"  postgresql://postgres.{args.ref}:[YOUR-PASSWORD]@{host}:6543/postgres")


if __name__ == "__main__":
    main(sys.argv[1:])

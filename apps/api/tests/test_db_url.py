import pytest
from sqlalchemy.engine import make_url

from app.db import connection_problem, normalize_url


def parsed(url: str):
    return make_url(normalize_url(url))


def test_a_password_with_a_raw_at_sign_is_repaired_and_parses_correctly():
    u = parsed("postgresql://postgres:pa@ss2026@db.abcdefgh.supabase.co:5432/postgres")
    assert u.password == "pa@ss2026" and u.host == "db.abcdefgh.supabase.co" and u.port == 5432 and u.database == "postgres"


def test_several_raw_at_signs_are_fine_too():
    u = parsed("postgres://postgres.abc:a@b@c@aws-0-ap-northeast-1.pooler.supabase.com:6543/postgres")
    assert u.username == "postgres.abc" and u.password == "a@b@c" and u.host == "aws-0-ap-northeast-1.pooler.supabase.com"


@pytest.mark.parametrize(
    "url",
    [
        "postgresql://postgres.abc:p%40ss@aws-0-x.pooler.supabase.com:6543/postgres",  # already encoded
        "postgresql://u:plain@host:5432/db",  # nothing to repair
        "postgresql://u@host/db",  # no password at all
        "sqlite:///./vantage.db",
        "",
    ],
)
def test_addresses_that_were_fine_are_left_alone(url):
    expected = "postgresql+psycopg://" + url[len("postgresql://"):] if url.startswith("postgresql://") else url
    assert normalize_url(url) == expected


def test_an_encoded_password_is_not_encoded_twice():
    assert parsed("postgresql://u:p%40ss@host:5432/db").password == "p@ss"


def test_a_percent_sign_that_is_not_an_escape_survives():
    assert parsed("postgresql://u:50%off@x@host:5432/db").password == "50%off@x"


def test_the_direct_supabase_address_gets_a_plain_warning():
    message = connection_problem("postgresql://postgres:secret@db.xcczkaaytuqyhnhzlcge.supabase.co:5432/postgres")
    assert message and "Transaction pooler" in message and "IPv6" in message
    assert "secret" not in message and "xcczkaaytuqyhnhzlcge" not in message  # never echoes what was typed


@pytest.mark.parametrize(
    "url",
    [
        "postgresql://postgres.abc:pw@aws-0-ap-northeast-1.pooler.supabase.com:6543/postgres",
        "postgresql://u:p@localhost:5432/vantage",
        "sqlite:///./vantage.db",
        "",
    ],
)
def test_working_addresses_get_no_warning(url):
    assert connection_problem(url) is None

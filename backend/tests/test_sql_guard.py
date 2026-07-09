import pytest

from app.sql_guard import UnsafeQueryError, assert_read_only

ALLOWED_STARTS = ["SELECT", "WITH", "SHOW", "DESCRIBE", "EXPLAIN"]
FORBIDDEN_KEYWORDS = [
    "INSERT",
    "UPDATE",
    "DELETE",
    "MERGE",
    "DROP",
    "ALTER",
    "CREATE",
    "TRUNCATE",
    "GRANT",
    "REVOKE",
    "CALL",
    "COMMENT",
    "USE",
]


@pytest.mark.parametrize("keyword", ALLOWED_STARTS)
def test_allowed_start_passes(keyword):
    assert_read_only(f"{keyword} * FROM iceberg.marts.curated_events")


@pytest.mark.parametrize("keyword", ALLOWED_STARTS)
def test_allowed_start_is_case_insensitive(keyword):
    assert_read_only(f"{keyword.lower()} * from iceberg.marts.curated_events")


@pytest.mark.parametrize("keyword", FORBIDDEN_KEYWORDS)
def test_forbidden_keyword_raises(keyword):
    with pytest.raises(UnsafeQueryError):
        assert_read_only(f"SELECT * FROM t WHERE 1=1 {keyword} something")


def test_semicolon_separated_statements_raise():
    with pytest.raises(UnsafeQueryError):
        assert_read_only("SELECT 1; SELECT 2")


def test_disallowed_start_raises():
    with pytest.raises(UnsafeQueryError):
        assert_read_only("UPDATE t SET x = 1")

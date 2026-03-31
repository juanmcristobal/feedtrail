from datetime import datetime, timezone

from feedtrail.utils import date_utils


def test_auto_convert_date_invalid_inputs():
    assert date_utils.auto_convert_date(None) is None
    assert date_utils.auto_convert_date(123) is None
    assert date_utils.auto_convert_date("") is None


def test_auto_convert_date_rfc_and_zulu_parsing():
    value = date_utils.auto_convert_date("Wed, 20 Mar 2024 09:00:00 GMT")
    assert value == "2024-03-20T09:00:00"

    iso = date_utils.auto_convert_date("2024-03-20T09:00:00Z")
    assert iso == "2024-03-20T09:00:00"


def test_auto_convert_date_clamps_future_values():
    value = date_utils.auto_convert_date("Wed, 20 Mar 2999 09:00:00 GMT")
    assert value is not None

    parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
    assert parsed <= datetime.now(timezone.utc)


def test_auto_convert_date_month_pattern_and_custom_format(monkeypatch):
    monkeypatch.setattr(date_utils, "parsedate_to_datetime", lambda _s: None)
    value = date_utils.auto_convert_date(
        "Published on May 29, 2025", output_format="%Y-%m-%d"
    )
    assert value == "2025-05-29"


def test_auto_convert_date_returns_none_when_every_parser_fails(monkeypatch):
    monkeypatch.setattr(date_utils, "parsedate_to_datetime", lambda _s: None)
    monkeypatch.setattr(
        date_utils.parser,
        "parse",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(ValueError("boom")),
    )

    assert date_utils.auto_convert_date("this is not a date value") is None


def test_auto_convert_date_last_attempt_chunk_branch(monkeypatch):
    monkeypatch.setattr(date_utils, "parsedate_to_datetime", lambda _s: None)
    monkeypatch.setattr(
        date_utils.parser,
        "parse",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(ValueError("boom")),
    )

    value = date_utils.auto_convert_date("xx Tue, 20 Mar 2024 10:30:45 -04:00 yy")
    assert value == "2024-03-20T14:30:45"


def test_auto_convert_date_uses_dateutil_flexible_branch(monkeypatch):
    monkeypatch.setattr(date_utils, "parsedate_to_datetime", lambda _s: None)

    value = date_utils.auto_convert_date("20th of March 2024 at 10:30pm CET")
    assert value == "2024-03-20T21:30:00"


def test_auto_convert_date_future_clamps_on_other_branches(monkeypatch):
    monkeypatch.setattr(date_utils, "parsedate_to_datetime", lambda _s: None)
    common = date_utils.auto_convert_date("2999-01-01T00:00:00")
    assert common is not None

    month_pattern = date_utils.auto_convert_date("Published on May 29, 2999")
    assert month_pattern is not None

    monkeypatch.setattr(
        date_utils.parser,
        "parse",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(ValueError("boom")),
    )
    last = date_utils.auto_convert_date("xx Tue, 20 Mar 2999 10:30:45 -04:00 yy")
    assert last is not None

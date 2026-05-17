from datetime import date
from unittest.mock import MagicMock, patch
from config_loader import Route
from checker import _date_range, _parse_miles, AvailableAward


def test_date_range_inclusive():
    result = _date_range(date(2026, 7, 1), date(2026, 7, 3))
    assert result == [date(2026, 7, 1), date(2026, 7, 2), date(2026, 7, 3)]


def test_date_range_single_day():
    result = _date_range(date(2026, 7, 1), date(2026, 7, 1))
    assert result == [date(2026, 7, 1)]


def test_parse_miles_plain_number():
    assert _parse_miles("35000 miles") == 35000


def test_parse_miles_with_comma():
    assert _parse_miles("35,000 miles") == 35000


def test_parse_miles_k_suffix():
    assert _parse_miles("35K miles") == 35000


def test_parse_miles_lowercase_k():
    assert _parse_miles("35k") == 35000


def test_parse_miles_unrecognised_returns_none():
    assert _parse_miles("Not available") is None
    assert _parse_miles("") is None


def test_check_one_returns_empty_on_timeout():
    from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
    import checker

    mock_browser = MagicMock()
    mock_page = MagicMock()
    mock_browser.new_page.return_value = mock_page
    mock_page.goto.side_effect = PlaywrightTimeoutError("timeout")

    route = Route("CGO", "JFK", "economy")
    result = checker._check_one(mock_browser, route, date(2026, 7, 1))
    assert result == []
    mock_page.close.assert_called_once()


def test_check_one_returns_empty_on_captcha():
    import checker

    mock_browser = MagicMock()
    mock_page = MagicMock()
    mock_browser.new_page.return_value = mock_page
    mock_page.goto.return_value = None

    route = Route("CGO", "JFK", "economy")
    with patch.object(checker, "_dismiss_cookie_banner"), \
         patch.object(checker, "_fill_search_form"), \
         patch.object(checker, "_submit_search"), \
         patch.object(checker, "_has_captcha", return_value=True):
        result = checker._check_one(mock_browser, route, date(2026, 7, 1))

    assert result == []
    mock_page.close.assert_called_once()


def test_check_one_returns_empty_on_post_search_captcha():
    import checker

    mock_browser = MagicMock()
    mock_page = MagicMock()
    mock_browser.new_page.return_value = mock_page
    mock_page.goto.return_value = None

    route = Route("CGO", "JFK", "economy")
    # First call (pre-form) returns False, second call (post-search) returns True
    captcha_side_effects = [False, True]
    with patch.object(checker, "_dismiss_cookie_banner"), \
         patch.object(checker, "_fill_search_form"), \
         patch.object(checker, "_submit_search"), \
         patch.object(checker, "_has_captcha", side_effect=captcha_side_effects):
        result = checker._check_one(mock_browser, route, date(2026, 7, 1))

    assert result == []
    mock_page.close.assert_called_once()

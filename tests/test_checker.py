from datetime import date
from unittest.mock import patch, MagicMock, call
import requests

from config_loader import Route, Config
from checker import check_all, _check_route, _fetch_available_dates, AvailableAward, CABIN_MAP


def _make_config(**overrides):
    defaults = dict(
        routes=[Route("CGO", "JFK", "economy")],
        date_start=date(2026, 7, 1),
        date_end=date(2026, 7, 31),
        interval_hours=6,
        notify_on_empty=True,
        telegram_bot_token="tok",
        telegram_chat_id="123",
        headless=True,
    )
    defaults.update(overrides)
    return Config(**defaults)


def _api_response(entries):
    mock = MagicMock()
    mock.json.return_value = {"availabilities": {"std": entries, "pt1": [], "pt2": []}}
    mock.raise_for_status.return_value = None
    return mock


# --- cabin mapping ---

def test_cabin_map_covers_all_cabins():
    assert CABIN_MAP["economy"] == "eco"
    assert CABIN_MAP["business"] == "bus"
    assert CABIN_MAP["first"] == "fir"


# --- direct route ---

def test_direct_route_returns_awards_for_available_dates():
    route = Route("HKG", "JFK", "economy")
    entries = [
        {"date": "20260701", "availability": "H"},
        {"date": "20260702", "availability": "NA"},
        {"date": "20260703", "availability": "L"},
    ]
    with patch("checker.requests.get", return_value=_api_response(entries)):
        results = _check_route(route, date(2026, 7, 1), date(2026, 7, 31))

    assert len(results) == 2
    assert results[0].date == date(2026, 7, 1)
    assert results[0].route == route
    assert results[0].miles_required is None
    assert results[1].date == date(2026, 7, 3)


def test_direct_route_returns_empty_when_all_na():
    route = Route("HKG", "JFK", "economy")
    entries = [{"date": "20260701", "availability": "NA"}] * 31
    with patch("checker.requests.get", return_value=_api_response(entries)):
        results = _check_route(route, date(2026, 7, 1), date(2026, 7, 31))
    assert results == []


def test_direct_route_returns_empty_on_timeout():
    route = Route("HKG", "JFK", "economy")
    with patch("checker.requests.get", side_effect=requests.Timeout):
        results = _check_route(route, date(2026, 7, 1), date(2026, 7, 31))
    assert results == []


def test_direct_route_returns_empty_on_http_error():
    route = Route("HKG", "JFK", "economy")
    mock = MagicMock()
    mock.raise_for_status.side_effect = requests.HTTPError("503")
    with patch("checker.requests.get", return_value=mock):
        results = _check_route(route, date(2026, 7, 1), date(2026, 7, 31))
    assert results == []


def test_direct_route_uses_correct_cabin_code():
    route = Route("HKG", "JFK", "business")
    with patch("checker.requests.get", return_value=_api_response([])) as mock_get:
        _check_route(route, date(2026, 7, 1), date(2026, 7, 31))
    assert "bus" in mock_get.call_args[0][0]


def test_direct_route_builds_url_with_correct_dates():
    route = Route("HKG", "JFK", "economy")
    with patch("checker.requests.get", return_value=_api_response([])) as mock_get:
        _check_route(route, date(2026, 7, 1), date(2026, 7, 31))
    url = mock_get.call_args[0][0]
    assert "20260701" in url
    assert "20260731" in url


# --- connecting route (via) ---

def test_connecting_route_returns_dates_where_both_legs_available():
    route = Route("CGO", "JFK", "economy", via="HKG")
    leg1 = [
        {"date": "20260722", "availability": "H"},
        {"date": "20260723", "availability": "H"},
        {"date": "20260724", "availability": "NA"},
    ]
    leg2 = [
        {"date": "20260722", "availability": "H"},
        {"date": "20260723", "availability": "H"},
        {"date": "20260724", "availability": "NA"},
    ]
    responses = [_api_response(leg1), _api_response(leg2)]
    with patch("checker.requests.get", side_effect=responses):
        results = _check_route(route, date(2026, 7, 1), date(2026, 7, 31))

    assert len(results) == 1
    assert results[0].date == date(2026, 7, 22)
    assert results[0].route == route


def test_connecting_route_returns_empty_when_no_overlap():
    route = Route("CGO", "JFK", "economy", via="HKG")
    leg1 = [{"date": "20260722", "availability": "H"}]
    leg2 = [{"date": "20260724", "availability": "H"}]
    with patch("checker.requests.get", side_effect=[_api_response(leg1), _api_response(leg2)]):
        results = _check_route(route, date(2026, 7, 1), date(2026, 7, 31))
    assert results == []


def test_connecting_route_returns_empty_when_leg1_fails():
    route = Route("CGO", "JFK", "economy", via="HKG")
    with patch("checker.requests.get", side_effect=requests.Timeout):
        results = _check_route(route, date(2026, 7, 1), date(2026, 7, 31))
    assert results == []


def test_connecting_route_makes_two_api_calls():
    route = Route("CGO", "JFK", "economy", via="HKG")
    with patch("checker.requests.get", return_value=_api_response([])) as mock_get:
        _check_route(route, date(2026, 7, 1), date(2026, 7, 31))
    assert mock_get.call_count == 2


# --- check_all ---

def test_check_all_aggregates_results_across_routes():
    routes = [Route("HKG", "JFK", "economy"), Route("HKG", "LHR", "economy")]
    config = _make_config(routes=routes)
    entries = [{"date": "20260715", "availability": "H"}]

    with patch("checker.requests.get", return_value=_api_response(entries)):
        results = check_all(config)

    assert len(results) == 2
    assert results[0].route == routes[0]
    assert results[1].route == routes[1]


def test_check_all_returns_empty_when_no_availability():
    config = _make_config()
    with patch("checker.requests.get", return_value=_api_response([])):
        results = check_all(config)
    assert results == []

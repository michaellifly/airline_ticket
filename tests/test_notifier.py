from datetime import date
from unittest.mock import patch, MagicMock
from config_loader import Config, Route
from checker import AvailableAward
import notifier


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


def test_send_available_posts_to_telegram():
    config = _make_config()
    award = AvailableAward(
        date=date(2026, 7, 15),
        route=Route("CGO", "JFK", "economy"),
        miles_required=35000,
    )
    with patch("notifier.requests.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_post.return_value = mock_resp
        notifier.send_available(config, award)
    mock_post.assert_called_once()
    mock_resp.raise_for_status.assert_called_once()
    payload = mock_post.call_args.kwargs["json"]
    assert payload["chat_id"] == "123"
    assert "CGO" in payload["text"]
    assert "JFK" in payload["text"]
    assert "35,000" in payload["text"]
    assert "2026-07-15" in payload["text"]


def test_send_empty_posts_when_notify_on_empty_true():
    config = _make_config(notify_on_empty=True)
    route = Route("CGO", "JFK", "economy")
    with patch("notifier.requests.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_post.return_value = mock_resp
        notifier.send_empty(config, route, date(2026, 7, 1), date(2026, 7, 31), 6)
    mock_post.assert_called_once()
    mock_resp.raise_for_status.assert_called_once()
    payload = mock_post.call_args.kwargs["json"]
    assert "CGO" in payload["text"]
    assert "JFK" in payload["text"]
    assert "6 hours" in payload["text"]
    assert "Jul" in payload["text"]


def test_send_empty_skips_when_notify_on_empty_false():
    config = _make_config(notify_on_empty=False)
    route = Route("CGO", "JFK", "economy")
    with patch("notifier.requests.post") as mock_post:
        notifier.send_empty(config, route, date(2026, 7, 1), date(2026, 7, 31), 6)
    mock_post.assert_not_called()


def test_send_available_handles_none_miles():
    config = _make_config()
    award = AvailableAward(
        date=date(2026, 7, 15),
        route=Route("CGO", "JFK", "economy"),
        miles_required=None,
    )
    with patch("notifier.requests.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_post.return_value = mock_resp
        notifier.send_available(config, award)
    payload = mock_post.call_args.kwargs["json"]
    assert "check site" in payload["text"]


def test_send_available_logs_error_on_failure():
    config = _make_config()
    award = AvailableAward(
        date=date(2026, 7, 15),
        route=Route("CGO", "JFK", "economy"),
        miles_required=35000,
    )
    import requests as req
    with patch("notifier.requests.post", side_effect=req.RequestException("timeout")):
        notifier.send_available(config, award)  # must not raise

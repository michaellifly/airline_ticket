import pytest
from datetime import date
from config_loader import load_config, Config, Route

VALID_YAML = """
routes:
  - origin: CGO
    destination: JFK
    cabin: economy
dates:
  start: "2026-07-01"
  end: "2026-07-31"
schedule:
  interval_hours: 6
notify_on_empty: true
telegram:
  bot_token: "tok123"
  chat_id: "456"
playwright:
  headless: true
"""

def test_load_valid_config(tmp_path):
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text(VALID_YAML)
    config = load_config(str(cfg_file))
    assert isinstance(config, Config)
    assert len(config.routes) == 1
    assert config.routes[0] == Route(origin="CGO", destination="JFK", cabin="economy")
    assert config.date_start == date(2026, 7, 1)
    assert config.date_end == date(2026, 7, 31)
    assert config.interval_hours == 6
    assert config.notify_on_empty is True
    assert config.telegram_bot_token == "tok123"
    assert config.telegram_chat_id == "456"
    assert config.headless is True

def test_missing_config_file_exits():
    with pytest.raises(SystemExit):
        load_config("/nonexistent/config.yaml")

def test_missing_required_key_exits(tmp_path):
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text("routes: []\n")
    with pytest.raises(SystemExit):
        load_config(str(cfg_file))

def test_notify_on_empty_defaults_true(tmp_path):
    yaml_without_flag = VALID_YAML.replace("notify_on_empty: true\n", "")
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text(yaml_without_flag)
    config = load_config(str(cfg_file))
    assert config.notify_on_empty is True

def test_headless_defaults_true(tmp_path):
    yaml_without_playwright = VALID_YAML.replace("playwright:\n  headless: true\n", "")
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text(yaml_without_playwright)
    config = load_config(str(cfg_file))
    assert config.headless is True

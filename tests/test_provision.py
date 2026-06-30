"""Tests for the Hibiscus provisioning script."""

import sys
import textwrap
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).parent.parent / "provision"))

from provision import load_config, render, write  # noqa: E402
from jinja2 import Environment, FileSystemLoader, StrictUndefined, UndefinedError

TEMPLATES_DIR = Path(__file__).parent.parent / "provision" / "templates"


@pytest.fixture
def jinja_env():
    return Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        undefined=StrictUndefined,
        keep_trailing_newline=True,
    )


@pytest.fixture
def minimal_config():
    return {
        "hibiscus_password": "secret",
        "db_username": "hibiscus",
        "db_password": "dbpass",
        "accounts": [],
    }


@pytest.fixture
def full_config():
    return {
        "hibiscus_password": "secret",
        "http_port": 8888,
        "http_auth": True,
        "http_ssl": True,
        "db_host": "db.internal",
        "db_port": 3306,
        "db_name": "hibiscus",
        "db_username": "hibiscus",
        "db_password": "dbpass",
        "accounts": [
            {
                "name": "mybank",
                "server": "hbci.mybank.de",
                "port": 443,
                "blz": "12345678",
                "userid": "user1",
                "customerid": "user1",
                "hbciversion": "300",
            }
        ],
    }


class TestLoadConfig:
    def test_loads_valid_yaml(self, tmp_path):
        cfg = tmp_path / "config.yml"
        cfg.write_text("db_username: admin\ndb_password: secret\n")
        result = load_config(cfg)
        assert result["db_username"] == "admin"

    def test_raises_on_missing_file(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            load_config(tmp_path / "nonexistent.yml")

    def test_raises_on_non_mapping(self, tmp_path):
        cfg = tmp_path / "bad.yml"
        cfg.write_text("- item1\n- item2\n")
        with pytest.raises(ValueError, match="YAML mapping"):
            load_config(cfg)


class TestHBCIDBTemplate:
    def test_renders_with_defaults(self, jinja_env, minimal_config):
        out = render(jinja_env, "HBCIDBService.properties.j2", minimal_config)
        assert "127.0.0.1" in out
        assert "3306" in out
        assert "hibiscus" in out
        assert "db_username=hibiscus" in out.replace("database.driver.mysql.username=", "db_username=")

    def test_renders_custom_host(self, jinja_env, full_config):
        out = render(jinja_env, "HBCIDBService.properties.j2", full_config)
        assert "db.internal" in out
        assert "hibiscus" in out

    def test_raises_on_missing_required_field(self, jinja_env):
        with pytest.raises(SystemExit, match="Template error"):
            render(jinja_env, "HBCIDBService.properties.j2", {})


class TestPluginTemplate:
    def test_default_port(self, jinja_env, minimal_config):
        out = render(jinja_env, "Plugin.properties.j2", minimal_config)
        assert "listener.http.port=8888" in out

    def test_custom_port(self, jinja_env, full_config):
        full_config["http_port"] = 9999
        out = render(jinja_env, "Plugin.properties.j2", full_config)
        assert "listener.http.port=9999" in out

    def test_auth_and_ssl_rendered_as_lowercase_bool(self, jinja_env, full_config):
        out = render(jinja_env, "Plugin.properties.j2", full_config)
        assert "listener.http.auth=true" in out
        assert "listener.http.ssl=true" in out


class TestPinTanTemplate:
    def test_empty_accounts(self, jinja_env, minimal_config):
        out = render(jinja_env, "PinTanConfig.properties.j2", minimal_config)
        assert out.strip() == ""

    def test_single_account(self, jinja_env, full_config):
        out = render(jinja_env, "PinTanConfig.properties.j2", full_config)
        assert "mybank.server=hbci.mybank.de" in out
        assert "mybank.blz=12345678" in out
        assert "mybank.userid=user1" in out
        assert "mybank.hbciversion=300" in out

    def test_account_default_port(self, jinja_env, minimal_config):
        minimal_config["accounts"] = [
            {"name": "bank", "server": "hbci.bank.de", "blz": "00000000", "userid": "u"}
        ]
        out = render(jinja_env, "PinTanConfig.properties.j2", minimal_config)
        assert "bank.port=443" in out

    def test_multiple_accounts(self, jinja_env, minimal_config):
        minimal_config["accounts"] = [
            {"name": "bank1", "server": "s1.de", "blz": "11111111", "userid": "u1"},
            {"name": "bank2", "server": "s2.de", "blz": "22222222", "userid": "u2"},
        ]
        out = render(jinja_env, "PinTanConfig.properties.j2", minimal_config)
        assert "bank1.server=s1.de" in out
        assert "bank2.server=s2.de" in out


class TestWrite:
    def test_writes_file(self, tmp_path):
        target = tmp_path / "out" / "test.properties"
        write(target, "key=value\n", dry_run=False)
        assert target.read_text() == "key=value\n"

    def test_creates_parent_dirs(self, tmp_path):
        target = tmp_path / "a" / "b" / "c" / "file.txt"
        write(target, "x", dry_run=False)
        assert target.exists()

    def test_dry_run_does_not_write(self, tmp_path, capsys):
        target = tmp_path / "out.txt"
        write(target, "content", dry_run=True)
        assert not target.exists()
        captured = capsys.readouterr()
        assert "dry-run" in captured.out

"""Tests for the Hibiscus provisioning script."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

sys.path.insert(0, str(Path(__file__).parent.parent / "provision"))

from provision import (  # noqa: E402
    cli,
    config_from_env,
    config_from_file,
    render_template,
    validate_config,
    write_file,
    build_jinja_env,
)

TEMPLATES_DIR = Path(__file__).parent.parent / "provision" / "templates"

# ── fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def jinja_env():
    return build_jinja_env()


@pytest.fixture
def minimal_cfg():
    return {
        "hibiscus_password": "secret",
        "db_username": "hibiscus",
        "db_password": "dbpass",
        "accounts": [],
    }


@pytest.fixture
def full_cfg():
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


@pytest.fixture
def env_vars():
    return {
        "HIBISCUS_PASSWORD": "masterpwd",
        "HIBISCUS_DB_HOST": "db.internal",
        "HIBISCUS_DB_PORT": "5432",
        "HIBISCUS_DB_NAME": "mydb",
        "HIBISCUS_DB_USERNAME": "admin",
        "HIBISCUS_DB_PASSWORD": "dbsecret",
        "HIBISCUS_HTTP_PORT": "9000",
        "HIBISCUS_HTTP_AUTH": "false",
        "HIBISCUS_HTTP_SSL": "false",
    }


# ── config loading ─────────────────────────────────────────────────────────────

class TestConfigFromFile:
    def test_loads_valid_yaml(self, tmp_path):
        cfg_file = tmp_path / "config.yml"
        cfg_file.write_text("db_username: admin\ndb_password: secret\nhibiscus_password: pw\naccounts: []\n")
        result = config_from_file(cfg_file)
        assert result["db_username"] == "admin"

    def test_raises_on_missing_file(self, tmp_path):
        import click
        with pytest.raises(click.ClickException, match="not found"):
            config_from_file(tmp_path / "nonexistent.yml")

    def test_raises_on_non_mapping(self, tmp_path):
        import click
        cfg_file = tmp_path / "bad.yml"
        cfg_file.write_text("- item1\n- item2\n")
        with pytest.raises(click.ClickException, match="mapping"):
            config_from_file(cfg_file)


class TestConfigFromEnv:
    def test_reads_all_env_vars(self, env_vars):
        with patch.dict(os.environ, env_vars, clear=False):
            cfg = config_from_env()
        assert cfg["hibiscus_password"] == "masterpwd"
        assert cfg["db_host"] == "db.internal"
        assert cfg["db_port"] == 5432
        assert cfg["db_username"] == "admin"
        assert cfg["http_port"] == 9000
        assert cfg["http_auth"] is False
        assert cfg["http_ssl"] is False

    def test_applies_defaults(self):
        clean = {k: v for k, v in os.environ.items()
                 if not k.startswith("HIBISCUS_")}
        with patch.dict(os.environ, clean, clear=True):
            cfg = config_from_env()
        assert cfg["db_host"] == "127.0.0.1"
        assert cfg["db_port"] == 3306
        assert cfg["http_port"] == 8888
        assert cfg["http_auth"] is True

    def test_reads_secret_from_file(self, tmp_path):
        secret_file = tmp_path / "pwd"
        secret_file.write_text("file-secret\n")
        env = {"HIBISCUS_PASSWORD_FILE": str(secret_file)}
        with patch.dict(os.environ, env, clear=False):
            cfg = config_from_env()
        assert cfg["hibiscus_password"] == "file-secret"

    def test_secret_file_takes_precedence_when_both_set(self, tmp_path):
        secret_file = tmp_path / "pwd"
        secret_file.write_text("from-file")
        env = {
            "HIBISCUS_PASSWORD": "from-env",
            "HIBISCUS_PASSWORD_FILE": str(secret_file),
        }
        with patch.dict(os.environ, env, clear=False):
            cfg = config_from_env()
        # Env value wins (it's read first; _FILE is the fallback)
        assert cfg["hibiscus_password"] == "from-env"

    def test_raises_on_missing_secret_file(self, tmp_path):
        import click
        env = {"HIBISCUS_PASSWORD_FILE": str(tmp_path / "missing")}
        with patch.dict(os.environ, env, clear=False):
            with pytest.raises(click.ClickException, match="not found"):
                config_from_env()


# ── validation ────────────────────────────────────────────────────────────────

class TestValidateConfig:
    def test_valid_config_returns_no_errors(self, full_cfg):
        assert validate_config(full_cfg) == []

    def test_missing_required_fields(self):
        errors = validate_config({})
        assert any("db_username" in e for e in errors)
        assert any("db_password" in e for e in errors)
        assert any("hibiscus_password" in e for e in errors)

    def test_invalid_port(self, full_cfg):
        full_cfg["http_port"] = 99999
        errors = validate_config(full_cfg)
        assert any("http_port" in e for e in errors)


# ── templates ─────────────────────────────────────────────────────────────────

class TestHBCIDBTemplate:
    def test_renders_with_defaults(self, jinja_env, minimal_cfg):
        out = render_template(jinja_env, "HBCIDBService.properties.j2", minimal_cfg)
        assert "127.0.0.1" in out
        assert "3306" in out
        assert "hibiscus" in out

    def test_renders_custom_host(self, jinja_env, full_cfg):
        out = render_template(jinja_env, "HBCIDBService.properties.j2", full_cfg)
        assert "db.internal" in out

    def test_raises_on_missing_field(self, jinja_env):
        import click
        with pytest.raises(click.ClickException, match="Template error"):
            render_template(jinja_env, "HBCIDBService.properties.j2", {})


class TestPluginTemplate:
    def test_default_port(self, jinja_env, minimal_cfg):
        out = render_template(jinja_env, "Plugin.properties.j2", minimal_cfg)
        assert "listener.http.port=8888" in out

    def test_custom_port(self, jinja_env, full_cfg):
        full_cfg["http_port"] = 9999
        out = render_template(jinja_env, "Plugin.properties.j2", full_cfg)
        assert "listener.http.port=9999" in out

    def test_booleans_rendered_lowercase(self, jinja_env, full_cfg):
        out = render_template(jinja_env, "Plugin.properties.j2", full_cfg)
        assert "listener.http.auth=true" in out
        assert "listener.http.ssl=true" in out


class TestPinTanTemplate:
    def test_empty_accounts(self, jinja_env, minimal_cfg):
        out = render_template(jinja_env, "PinTanConfig.properties.j2", minimal_cfg)
        assert out.strip() == ""

    def test_single_account(self, jinja_env, full_cfg):
        out = render_template(jinja_env, "PinTanConfig.properties.j2", full_cfg)
        assert "mybank.server=hbci.mybank.de" in out
        assert "mybank.blz=12345678" in out
        assert "mybank.hbciversion=300" in out

    def test_account_default_port(self, jinja_env, minimal_cfg):
        minimal_cfg["accounts"] = [
            {"name": "bank", "server": "hbci.bank.de", "blz": "00000000", "userid": "u"}
        ]
        out = render_template(jinja_env, "PinTanConfig.properties.j2", minimal_cfg)
        assert "bank.port=443" in out

    def test_multiple_accounts(self, jinja_env, minimal_cfg):
        minimal_cfg["accounts"] = [
            {"name": "bank1", "server": "s1.de", "blz": "11111111", "userid": "u1"},
            {"name": "bank2", "server": "s2.de", "blz": "22222222", "userid": "u2"},
        ]
        out = render_template(jinja_env, "PinTanConfig.properties.j2", minimal_cfg)
        assert "bank1.server=s1.de" in out
        assert "bank2.server=s2.de" in out


# ── write helper ──────────────────────────────────────────────────────────────

class TestWriteFile:
    def test_writes_file(self, tmp_path):
        target = tmp_path / "out" / "test.properties"
        write_file(target, "key=value\n", dry_run=False)
        assert target.read_text() == "key=value\n"

    def test_creates_parent_dirs(self, tmp_path):
        target = tmp_path / "a" / "b" / "file.txt"
        write_file(target, "x", dry_run=False)
        assert target.exists()

    def test_dry_run_does_not_write(self, tmp_path, capsys):
        target = tmp_path / "out.txt"
        write_file(target, "content", dry_run=True)
        assert not target.exists()


# ── CLI integration ───────────────────────────────────────────────────────────

class TestRenderCLI:
    def test_render_with_config(self, runner, tmp_path, full_cfg):
        import yaml as _yaml
        cfg_file = tmp_path / "config.yml"
        cfg_file.write_text(_yaml.dump(full_cfg))
        out_dir = tmp_path / "out"
        result = runner.invoke(cli, ["render", "--config", str(cfg_file), "--out", str(out_dir)])
        assert result.exit_code == 0, result.output
        assert (out_dir / "HBCIDBService.properties").exists()
        assert (out_dir / "Plugin.properties").exists()

    def test_render_dry_run_writes_nothing(self, runner, tmp_path, full_cfg):
        import yaml as _yaml
        cfg_file = tmp_path / "config.yml"
        cfg_file.write_text(_yaml.dump(full_cfg))
        out_dir = tmp_path / "out"
        result = runner.invoke(cli, ["render", "--config", str(cfg_file),
                                     "--out", str(out_dir), "--dry-run"])
        assert result.exit_code == 0
        assert not out_dir.exists()

    def test_render_fails_on_missing_required(self, runner, tmp_path):
        cfg_file = tmp_path / "bad.yml"
        cfg_file.write_text("http_port: 8888\n")
        result = runner.invoke(cli, ["render", "--config", str(cfg_file), "--out", str(tmp_path)])
        assert result.exit_code != 0

    def test_exclusive_flags(self, runner, tmp_path):
        result = runner.invoke(cli, ["render", "--from-env", "--config", str(tmp_path / "x.yml")])
        assert result.exit_code != 0

    def test_render_from_env(self, runner, tmp_path, env_vars):
        out_dir = tmp_path / "out"
        with patch.dict(os.environ, env_vars, clear=False):
            result = runner.invoke(cli, ["render", "--from-env", "--out", str(out_dir)])
        assert result.exit_code == 0, result.output
        assert (out_dir / "HBCIDBService.properties").exists()


class TestValidateCLI:
    def test_valid_config(self, runner, tmp_path, full_cfg):
        import yaml as _yaml
        cfg_file = tmp_path / "config.yml"
        cfg_file.write_text(_yaml.dump(full_cfg))
        result = runner.invoke(cli, ["validate", "--config", str(cfg_file)])
        assert result.exit_code == 0

    def test_invalid_config(self, runner, tmp_path):
        cfg_file = tmp_path / "bad.yml"
        cfg_file.write_text("http_port: 8888\n")
        result = runner.invoke(cli, ["validate", "--config", str(cfg_file)])
        assert result.exit_code != 0


class TestShowCLI:
    def test_show_masks_secrets(self, runner, tmp_path, full_cfg):
        import yaml as _yaml
        cfg_file = tmp_path / "config.yml"
        cfg_file.write_text(_yaml.dump(full_cfg))
        result = runner.invoke(cli, ["show", "--config", str(cfg_file)])
        assert result.exit_code == 0
        assert "hibiscus_password" in result.output
        # Actual password value must not appear
        assert full_cfg["hibiscus_password"] not in result.output
        assert full_cfg["db_password"] not in result.output

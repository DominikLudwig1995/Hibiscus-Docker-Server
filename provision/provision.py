#!/usr/bin/env python3
"""
Hibiscus provisioning CLI.

Renders Jinja2 config templates into Hibiscus .properties files.

Supports two input modes:
  --from-env   Read config from HIBISCUS_* environment variables
               (ideal for Docker / Kubernetes / Compose secrets)
  --config     Read config from a YAML file

Docker secret files are supported via the *_FILE convention:
  HIBISCUS_PASSWORD_FILE=/run/secrets/hibiscus_password

Usage:
  provision render --from-env [--out /path/to/cfg] [--dry-run]
  provision render --config config.yml [--out ./secrets] [--dry-run]
  provision validate --from-env
  provision validate --config config.yml
  provision show --from-env
  provision show --config config.yml
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

import click
import yaml
from jinja2 import Environment, FileSystemLoader, StrictUndefined, UndefinedError
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich import box

TEMPLATES_DIR = Path(__file__).parent / "templates"

# Maps template filename → output filename (relative to --out)
TEMPLATE_MAP: dict[str, str] = {
    "HBCIDBService.properties.j2": "HBCIDBService.properties",
    "PinTanConfig.properties.j2":  "PinTanConfig.properties",
    "Plugin.properties.j2":        "Plugin.properties",
}

# Required fields and their descriptions
REQUIRED_FIELDS: dict[str, str] = {
    "db_username": "Database username  (HIBISCUS_DB_USERNAME)",
    "db_password": "Database password  (HIBISCUS_DB_PASSWORD)",
    "hibiscus_password": "Hibiscus master password  (HIBISCUS_PASSWORD)",
}

console = Console()
err_console = Console(stderr=True)


# ── helpers ───────────────────────────────────────────────────────────────────

def _read_secret(value: str | None, file_env: str) -> str | None:
    """Return value, falling back to reading the file named in file_env."""
    if value:
        return value
    file_path = os.environ.get(file_env)
    if file_path:
        p = Path(file_path)
        if not p.exists():
            raise click.ClickException(f"Secret file not found: {p}  (from {file_env})")
        return p.read_text().strip()
    return None


def _bool_env(name: str, default: bool) -> bool:
    val = os.environ.get(name, "").lower()
    if val in ("1", "true", "yes"):
        return True
    if val in ("0", "false", "no"):
        return False
    return default


def config_from_env() -> dict[str, Any]:
    """Build a config dict from HIBISCUS_* environment variables."""
    return {
        # Hibiscus master password
        "hibiscus_password": _read_secret(
            os.environ.get("HIBISCUS_PASSWORD"),
            "HIBISCUS_PASSWORD_FILE",
        ),
        # Web interface
        "http_port": int(os.environ.get("HIBISCUS_HTTP_PORT", "8888")),
        "http_auth": _bool_env("HIBISCUS_HTTP_AUTH", True),
        "http_ssl":  _bool_env("HIBISCUS_HTTP_SSL", True),
        # Database
        "db_host":     os.environ.get("HIBISCUS_DB_HOST", "127.0.0.1"),
        "db_port":     int(os.environ.get("HIBISCUS_DB_PORT", "3306")),
        "db_name":     os.environ.get("HIBISCUS_DB_NAME", "hibiscus"),
        "db_username": _read_secret(
            os.environ.get("HIBISCUS_DB_USERNAME"),
            "HIBISCUS_DB_USERNAME_FILE",
        ),
        "db_password": _read_secret(
            os.environ.get("HIBISCUS_DB_PASSWORD"),
            "HIBISCUS_DB_PASSWORD_FILE",
        ),
        # Bank accounts — optional, read from HIBISCUS_ACCOUNTS_FILE
        "accounts": _load_accounts(),
    }


def _load_accounts() -> list[dict]:
    accounts_file = os.environ.get("HIBISCUS_ACCOUNTS_FILE")
    if not accounts_file:
        return []
    p = Path(accounts_file)
    if not p.exists():
        raise click.ClickException(f"Accounts file not found: {p}  (from HIBISCUS_ACCOUNTS_FILE)")
    data = yaml.safe_load(p.read_text())
    if not isinstance(data, list):
        raise click.ClickException(f"{p}: expected a YAML list of account objects")
    return data


def config_from_file(path: Path) -> dict[str, Any]:
    """Load config from a YAML file."""
    if not path.exists():
        raise click.ClickException(f"Config file not found: {path}")
    data = yaml.safe_load(path.read_text())
    if not isinstance(data, dict):
        raise click.ClickException(f"{path}: expected a YAML mapping at the top level")
    return data


def validate_config(cfg: dict[str, Any]) -> list[str]:
    """Return a list of validation error messages (empty = valid)."""
    errors: list[str] = []
    for field, description in REQUIRED_FIELDS.items():
        if not cfg.get(field):
            errors.append(f"Missing required field: {field}  —  {description}")
    http_port = cfg.get("http_port", 8888)
    if not (1 <= int(http_port) <= 65535):
        errors.append(f"http_port {http_port!r} is out of range (1–65535)")
    return errors


def build_jinja_env() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        undefined=StrictUndefined,
        keep_trailing_newline=True,
    )


def render_template(jinja_env: Environment, template_name: str, context: dict) -> str:
    try:
        return jinja_env.get_template(template_name).render(**context)
    except UndefinedError as exc:
        raise click.ClickException(f"Template error in {template_name}: {exc}") from exc


def write_file(path: Path, content: str, *, dry_run: bool) -> None:
    if dry_run:
        console.print(f"\n[bold cyan]──── {path} (dry-run) ────[/]")
        console.print(Syntax(content, "properties", theme="monokai", line_numbers=False))
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    console.print(f"  [green]✓[/]  {path}")


# ── CLI entry point ───────────────────────────────────────────────────────────

@click.group()
def cli() -> None:
    """Hibiscus Server provisioning tool."""


def _source_options(fn):
    fn = click.option(
        "--config", "-c", "config_path", type=click.Path(path_type=Path),
        help="YAML config file (mutually exclusive with --from-env)",
    )(fn)
    fn = click.option(
        "--from-env", "from_env", is_flag=True,
        help="Read config from HIBISCUS_* environment variables",
    )(fn)
    return fn


def _load_config(config_path: Path | None, from_env: bool) -> dict[str, Any]:
    if from_env and config_path:
        raise click.UsageError("--from-env and --config are mutually exclusive")
    if not from_env and not config_path:
        raise click.UsageError("Provide either --from-env or --config <file>")
    return config_from_env() if from_env else config_from_file(config_path)


# ── render ────────────────────────────────────────────────────────────────────

@cli.command()
@_source_options
@click.option("--out", "-o", type=click.Path(path_type=Path), default=Path("secrets"),
              show_default=True, help="Output directory for rendered files")
@click.option("--dry-run", is_flag=True, help="Print rendered output; do not write files")
def render(config_path: Path | None, from_env: bool, out: Path, dry_run: bool) -> None:
    """Render Jinja2 templates → Hibiscus .properties files."""
    cfg = _load_config(config_path, from_env)

    errors = validate_config(cfg)
    if errors:
        err_console.print(Panel(
            "\n".join(f"[red]✗[/]  {e}" for e in errors),
            title="[bold red]Configuration errors[/]",
            border_style="red",
        ))
        sys.exit(1)

    mode = "(dry-run)" if dry_run else str(out)
    console.print(Panel(
        f"[bold]Source:[/] {'environment variables' if from_env else config_path}\n"
        f"[bold]Output:[/] {mode}",
        title="[bold blue]Hibiscus Provisioner[/]",
        border_style="blue",
    ))

    jinja_env = build_jinja_env()

    for template_name, output_name in TEMPLATE_MAP.items():
        content = render_template(jinja_env, template_name, cfg)
        write_file(out / output_name, content, dry_run=dry_run)

    # Write master password
    pwd = cfg.get("hibiscus_password")
    if pwd:
        write_file(out / "pwd", str(pwd), dry_run=dry_run)

    if not dry_run:
        console.print("\n[bold green]✓ Provisioning complete.[/]")


# ── validate ──────────────────────────────────────────────────────────────────

@cli.command()
@_source_options
def validate(config_path: Path | None, from_env: bool) -> None:
    """Validate config without writing any files."""
    cfg = _load_config(config_path, from_env)
    errors = validate_config(cfg)

    if errors:
        err_console.print(Panel(
            "\n".join(f"[red]✗[/]  {e}" for e in errors),
            title="[bold red]Validation failed[/]",
            border_style="red",
        ))
        sys.exit(1)

    console.print(Panel("[green]✓  Config is valid[/]", border_style="green"))


# ── show ──────────────────────────────────────────────────────────────────────

@cli.command()
@_source_options
def show(config_path: Path | None, from_env: bool) -> None:
    """Display the resolved config (secrets are masked)."""
    cfg = _load_config(config_path, from_env)

    def mask(v: Any) -> str:
        if v is None:
            return "[dim]<not set>[/]"
        s = str(v)
        return "[yellow]<set>[/]" if s else "[dim]<empty>[/]"

    secret_keys = {"hibiscus_password", "db_password"}

    table = Table(box=box.ROUNDED, show_header=True, header_style="bold magenta")
    table.add_column("Key", style="cyan", no_wrap=True)
    table.add_column("Value")

    for k, v in cfg.items():
        if k == "accounts":
            table.add_row(k, f"[dim]{len(v)} account(s)[/]")
        elif k in secret_keys:
            table.add_row(k, mask(v))
        else:
            table.add_row(k, str(v) if v is not None else "[dim]<not set>[/]")

    console.print(Panel(table, title="[bold]Resolved config[/]", border_style="blue"))

    errors = validate_config(cfg)
    if errors:
        err_console.print("\n[bold red]Validation issues:[/]")
        for e in errors:
            err_console.print(f"  [red]✗[/]  {e}")


if __name__ == "__main__":
    cli()

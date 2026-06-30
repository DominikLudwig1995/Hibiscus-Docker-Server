#!/usr/bin/env python3
"""
Hibiscus provisioning script.

Renders Jinja2 config templates from a YAML config file and writes the
resulting files to a target directory (default: ./secrets/).

Usage:
    python provision.py --config config.yml [--out ./secrets]
    python provision.py --config config.yml --dry-run
"""

import argparse
import os
import sys
from pathlib import Path

try:
    import yaml
    from jinja2 import Environment, FileSystemLoader, StrictUndefined, UndefinedError
except ImportError:
    print("Missing dependencies. Run: pip install jinja2 pyyaml", file=sys.stderr)
    sys.exit(1)


TEMPLATES_DIR = Path(__file__).parent / "templates"

TEMPLATE_MAP = {
    "HBCIDBService.properties.j2": "HBCIDBService.properties",
    "PinTanConfig.properties.j2": "PinTanConfig.properties",
    "Plugin.properties.j2": "Plugin.properties",
}


def load_config(path: Path) -> dict:
    with path.open() as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a YAML mapping at the top level")
    return data


def render(env: Environment, template_name: str, context: dict) -> str:
    try:
        return env.get_template(template_name).render(**context)
    except UndefinedError as exc:
        raise SystemExit(f"Template error in {template_name}: {exc}") from exc


def write(path: Path, content: str, dry_run: bool) -> None:
    if dry_run:
        print(f"[dry-run] would write {path}:\n{content}\n{'─' * 60}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    print(f"  wrote  {path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Provision Hibiscus config files from Jinja2 templates")
    parser.add_argument("--config", required=True, type=Path, help="Path to config YAML file")
    parser.add_argument("--out", type=Path, default=Path("secrets"), help="Output directory (default: ./secrets)")
    parser.add_argument("--dry-run", action="store_true", help="Print rendered output without writing files")
    args = parser.parse_args()

    if not args.config.exists():
        raise SystemExit(f"Config file not found: {args.config}")

    context = load_config(args.config)

    jinja_env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        undefined=StrictUndefined,
        keep_trailing_newline=True,
    )

    print(f"Provisioning into {'(dry run)' if args.dry_run else args.out} ...")
    for template_name, output_name in TEMPLATE_MAP.items():
        content = render(jinja_env, template_name, context)
        write(args.out / output_name, content, args.dry_run)

    if not args.dry_run:
        # Write master password file
        pwd = context.get("hibiscus_password")
        if pwd is not None:
            write(args.out / "pwd", str(pwd), dry_run=False)
        else:
            print("  [skip]  hibiscus_password not set — pwd file not written")

    print("Done.")


if __name__ == "__main__":
    main()

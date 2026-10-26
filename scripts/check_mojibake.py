#!/usr/bin/env python3
"""Fail on `cat -v` notation (M-pM-^_...) that ended up in text files.

Such text is the shell's rendering of UTF-8 bytes, e.g. a copied terminal
output. Only runs that decode to valid UTF-8 are reported, so ordinary text
like "M-Bahn" stays untouched.

With file arguments (pre-commit) only those files are checked; without
arguments the whole working tree is walked (CI).
"""

import os
import re
import sys

TOKEN = r"(?:M-\^[@-_]|M-[ -~])"
RUN = re.compile(rf"(?:{TOKEN}){{2,}}")
ONE = re.compile(r"M-\^([@-_])|M-([ -~])")
SKIP_DIRS = {
    ".git",
    "node_modules",
    ".venv",
    "venv",
    "__pycache__",
    "dist",
    "build",
    ".next",
    "target",
}
SKIP_EXT = (
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".ico",
    ".pdf",
    ".woff",
    ".woff2",
    ".ttf",
    ".zip",
    ".gz",
    ".lock",
    ".svg",
    ".xlsx",
    ".docx",
    ".tar",
    ".zst",
    ".jar",
    ".bin",
    ".pyc",
    ".webp",
    ".mp4",
)
SELF = os.path.basename(__file__)


def decodes(run):
    data = bytearray()
    for m in ONE.finditer(run):
        low = ord(m.group(1)) - 64 if m.group(1) else ord(m.group(2))
        data.append(0x80 | low)
    try:
        bytes(data).decode("utf-8")
    except UnicodeDecodeError:
        return False
    return True


def walk(root):
    for base, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for name in files:
            if name.lower().endswith(SKIP_EXT) or name in ("package-lock.json", SELF):
                continue
            yield os.path.join(base, name)


def main(paths):
    bad = 0
    for path in paths or walk("."):
        if os.path.basename(path) == SELF:
            continue
        try:
            with open(path, encoding="utf-8") as fh:
                text = fh.read()
        except (OSError, UnicodeDecodeError):
            continue
        for no, line in enumerate(text.splitlines(), 1):
            if any(decodes(m.group(0)) for m in RUN.finditer(line)):
                print(f"{path}:{no}: cat -v notation instead of real characters")
                bad = 1
    return bad


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

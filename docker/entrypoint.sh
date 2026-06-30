#!/usr/bin/env bash
# Container entrypoint: provision config then hand off to Hibiscus.
# Exits immediately on any error.
set -euo pipefail

CFG_DIR="/home/hibiscus/hibiscus-server/cfg"
PWD_FILE="/home/hibiscus/hibiscus-server/pwd"

# Render all .properties files + password file into the Hibiscus cfg directory.
/opt/venv/bin/python /opt/provision/provision.py render \
    --from-env \
    --out "${CFG_DIR}"

# The password was written to cfg/pwd by the provisioner; move it one level up
# so it is not accidentally served by the webadmin plugin.
if [[ -f "${CFG_DIR}/pwd" ]]; then
    mv "${CFG_DIR}/pwd" "${PWD_FILE}"
fi

# Hand off to Hibiscus — exec replaces this process so signals are forwarded.
exec ./hibiscus-server/jameicaserver.sh -w "${PWD_FILE}"

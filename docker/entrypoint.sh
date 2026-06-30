#!/usr/bin/env bash
# Container entrypoint: provision config then hand off to Hibiscus.
set -euo pipefail

CFG_DIR="/home/hibiscus/hibiscus-server/cfg"
PWD_FILE="/home/hibiscus/hibiscus-server/pwd"

# Render all .properties files + password file into the Hibiscus cfg directory.
python /opt/provision/provision.py render \
    --from-env \
    --out "${CFG_DIR}"

# Move password file one level up so it is not served by the webadmin plugin,
# then restrict permissions so only the hibiscus user can read it.
if [[ -f "${CFG_DIR}/pwd" ]]; then
    mv "${CFG_DIR}/pwd" "${PWD_FILE}"
    chmod 600 "${PWD_FILE}"
fi

# exec replaces this process so signals (SIGTERM, SIGINT) are forwarded to the JVM.
exec /home/hibiscus/hibiscus-server/jameicaserver.sh -w "${PWD_FILE}"

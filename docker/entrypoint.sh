#!/usr/bin/env bash
# Container entrypoint: provision config then hand off to Hibiscus.
set -euo pipefail

# Jameica reads plugin config from its workdir (~/.jameica/cfg), not from the
# bundled hibiscus-server/cfg directory. Writing there directly means Jameica
# finds our provisioned files already in place and does not overwrite them with
# its bundled defaults on first boot.
JAMEICA_DIR="/home/hibiscus/.jameica"
CFG_DIR="${JAMEICA_DIR}/cfg"
PWD_FILE="/home/hibiscus/hibiscus-server/pwd"

mkdir -p "${CFG_DIR}"

# Render all .properties files + password file into the Jameica config dir.
python /opt/provision/provision.py render \
    --from-env \
    --out "${CFG_DIR}"

# Move password file out of the cfg directory so it is not accidentally served
# by the webadmin plugin, then restrict read access to the hibiscus user only.
if [[ -f "${CFG_DIR}/pwd" ]]; then
    mv "${CFG_DIR}/pwd" "${PWD_FILE}"
    chmod 600 "${PWD_FILE}"
fi

# exec replaces this process so signals (SIGTERM, SIGINT) are forwarded to the JVM.
exec /home/hibiscus/hibiscus-server/jameicaserver.sh -w "${PWD_FILE}"

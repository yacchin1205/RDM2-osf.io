#!/bin/bash
set -euo pipefail
set -x

if [ "$#" -ne 1 ]; then
    echo "usage: $0 <TEST_BUILD>" >&2
    exit 1
fi

TEST_BUILD="$1"
REPO_ROOT=$(git rev-parse --show-toplevel)
cd "$REPO_ROOT"

compose_files=(-f docker-compose.yml -f .github/docker-compose.ci.override.yml)
compose() {
    docker compose "${compose_files[@]}" "$@"
}

cleanup() {
    compose down -v
}
trap cleanup EXIT

cp website/settings/local-travis.py website/settings/local.py
cp api/base/settings/local-travis.py api/base/settings/local.py
cp tasks/local-dist.py tasks/local.py
printf "\nDB_HOST = 'postgres'\nDB_PORT = 5432\nELASTIC_URI = 'elasticsearch:9200'\n" \
    >> website/settings/local.py

# Setup loopback alias for container communication
sudo ip addr add 192.168.168.167/32 dev lo

compose pull postgres elasticsearch6
compose build elasticsearch
compose up -d postgres elasticsearch elasticsearch6

for _ in $(seq 1 60); do
    if compose exec -T postgres pg_isready -h localhost -p 5432 -U postgres; then
        break
    fi
    sleep 5
done

if ! compose exec -T postgres pg_isready -h localhost -p 5432 -U postgres; then
    echo "postgres did not become ready" >&2
    exit 1
fi

for url in "http://localhost:9200/_cluster/health?wait_for_status=yellow" "http://localhost:9201/_cluster/health?wait_for_status=yellow"; do
    for _ in $(seq 1 60); do
        if curl -fS "$url"; then
            break
        fi
        sleep 5
    done
    if ! curl -fS "$url"; then
        echo "elasticsearch endpoint $url did not respond" >&2
        exit 1
    fi
done

compose run --rm requirements

container_script=$(cat <<'BASH'
set -euo pipefail
set -x
export PATH="/usr/local/bin:/usr/bin:$PATH"
python3 -m invoke travis-addon-settings
# Minimal Ember app shells so send_from_directory returns 200 during tests
mkdir -p "$HOME/preprints" "$HOME/website/ember_osf_web"
for ember_stub in "$HOME/preprints/index.html" "$HOME/website/ember_osf_web/index.html"; do
    if [ ! -f "$ember_stub" ]; then
        printf '<!doctype html><title>stub</title>' > "$ember_stub"
    fi
done
mkdir -p user_key_info
cp root_cert_verifycate.pem user_key_info/
if [ "$TEST_BUILD" = "api1_and_js" ]; then
    python3 -m invoke assets --dev
fi
python3 -m invoke "test-travis-${TEST_BUILD//_/-}" -n 1
BASH
)

compose run --rm \
    -e TEST_BUILD="$TEST_BUILD" \
    -e BOWER_ALLOW_ROOT=1 \
    -e NPM_CONFIG_FORCE=true \
    -e npm_config_force=true \
    web bash -lc "$container_script"

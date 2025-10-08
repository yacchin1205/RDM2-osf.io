#!/bin/bash
set -euo pipefail

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
    compose down -v >/dev/null 2>&1 || true
}
trap cleanup EXIT

cp website/settings/local-travis.py website/settings/local.py
cp api/base/settings/local-travis.py api/base/settings/local.py

python3 <<'PY'
from pathlib import Path
website_local = Path('website/settings/local.py')
website_local.write_text(website_local.read_text() + '\nDB_HOST = \'postgres\'\nDB_PORT = 5432\nELASTIC_URI = \'elasticsearch:9200\'\n')
PY

compose pull postgres elasticsearch6 web >/dev/null 2>&1 || true
compose build elasticsearch
compose up -d postgres elasticsearch elasticsearch6

for _ in $(seq 1 60); do
    if compose exec -T postgres pg_isready -h localhost -p 5432 -U postgres >/dev/null 2>&1; then
        break
    fi
    sleep 5
done

if ! compose exec -T postgres pg_isready -h localhost -p 5432 -U postgres >/dev/null 2>&1; then
    echo "postgres did not become ready" >&2
    exit 1
fi

for url in "http://localhost:9200/_cluster/health?wait_for_status=yellow" "http://localhost:9201/_cluster/health?wait_for_status=yellow"; do
    for _ in $(seq 1 60); do
        if curl -fs "$url" >/dev/null 2>&1; then
            break
        fi
        sleep 5
    done
    if ! curl -fs "$url" >/dev/null 2>&1; then
        echo "elasticsearch endpoint $url did not respond" >&2
        exit 1
    fi
done

read -r -d '' container_script <<'BASH' || true
set -euo pipefail
pip3 install --upgrade pip==21.1.3
pip3 install invoke==0.13.0
pip3 install flake8==2.4.0 --force-reinstall --upgrade
invoke travis_addon_settings
pip3 install psycopg2==2.7.3 --no-binary psycopg2
invoke requirements --dev --addons
pip3 uninstall uritemplate.py --yes || true
pip3 install uritemplate.py==0.3.0
if [ "$TEST_BUILD" = "api1_and_js" ]; then
    invoke assets --dev
fi
invoke "test_travis_${TEST_BUILD}" -n 1
BASH

compose run --rm \
    -e TEST_BUILD="$TEST_BUILD" \
    web bash -lc "$container_script"

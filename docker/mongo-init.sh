#!/usr/bin/env bash
# Placeholder. Mongo replica set initialization is handled by the healthcheck
# in docker-compose.yml (calls rs.initiate() if not already initiated).
# Kept here for future use (seed data, additional setup).
set -euo pipefail
echo "mongo-init.sh: replica set init delegated to healthcheck"

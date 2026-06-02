#!/bin/sh
set -eu

if [ -d /opt/isyone/scripts ]; then
  find /opt/isyone/scripts -type f -name '*.sh' -exec chmod 755 {} + || true
fi

exec uvicorn app.main:app --host 0.0.0.0 --port 8000

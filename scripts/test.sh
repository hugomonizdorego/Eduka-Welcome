#!/bin/sh
set -eu
project_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$project_root"
export QT_QPA_PLATFORM=offscreen
export QT_LOGGING_RULES='qt.text.font.db=false'
exec python3 -m unittest discover -s tests -v

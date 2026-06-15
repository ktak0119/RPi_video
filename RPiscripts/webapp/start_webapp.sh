#!/bin/bash

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

bash "$DIR/stop_webapp.sh"

nohup python3 "$DIR/app.py" >/dev/null 2>&1 &

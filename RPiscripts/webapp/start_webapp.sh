#!/bin/bash

# rpi-webapp.serviceでsystemd管理する場合はこのスクリプトは使わない
# (systemctl restart rpi-webapp.serviceを使うこと)。手動起動・デバッグ用。

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

bash "$DIR/stop_webapp.sh"

nohup python3 "$DIR/app.py" >/dev/null 2>&1 &

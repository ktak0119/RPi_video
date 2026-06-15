#!/bin/bash

# rpi-webapp.serviceでsystemd管理する場合はこのスクリプトは使わない
# (systemctl stop rpi-webapp.serviceを使うこと)。手動起動・デバッグ用。

pkill -f "RPi_video/app.py"

sleep 1

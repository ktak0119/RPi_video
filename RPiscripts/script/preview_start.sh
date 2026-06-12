#!/bin/bash

cd ~ || exit 1

bash script/preview_stop.sh

nohup python3 script/mjpeg_server.py >/dev/null 2>&1 &

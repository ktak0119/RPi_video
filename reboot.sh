#!/bin/bash

#set IP adress and port
source ~/setting/IP.txt
source ~/setting/sshSetting.txt	
source .bashrc

echo "IP" "$IP"

#stop preview
echo "Raspberry Pi を再起動します"

sleep 2

ssh2raspi $IP "sudo reboot"

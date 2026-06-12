#!/bin/bash

source ~/setting/sshSetting.txt
source .bashrc

echo "Raspberry Piとの接続を開始します"

sleep 2

##接続先の検索(HostTable.csvに登録されたIPへのpingスキャン)

hosts=()
ips=()

while IFS=',' read -r host ip; do
    [ "$host" == "host" ] && continue   # ヘッダ行スキップ
    [ -z "$ip" ] && continue            # IP未登録行スキップ
    if ping -c 1 -W 1 "$ip" >/dev/null 2>&1; then
        hosts+=("$host")
        ips+=("$ip")
    fi
done < ~/setting/HostTable.csv

##接続先の選択

if [ ${#hosts[@]} -eq 0 ]; then
    echo "応答のある機体が見つかりませんでした。IDを直接入力してください"

    result=$(termux-dialog text -t "セットアップ/更新したいカメラのIDを入力してください" -i "例: UT01")
    hostname=$(echo "$result" | jq -r '.text')

    IP=$(awk -F',' -v h="$hostname" '$1==h {print $2}' ~/setting/HostTable.csv)

else
    option_list=$(IFS=,; echo "${hosts[*]}")
    option_list="${option_list},手動入力"

    result=$(termux-dialog radio -v "$option_list" -t "セットアップ/更新するRPiを選んでください")
    index=$(echo "$result" | jq -r '.index')

    if [ "$index" == "${#hosts[@]}" ]; then
        result=$(termux-dialog text -t "セットアップ/更新したいカメラのIDを入力してください" -i "例: UT01")
        hostname=$(echo "$result" | jq -r '.text')

        IP=$(awk -F',' -v h="$hostname" '$1==h {print $2}' ~/setting/HostTable.csv)
    else
        hostname="${hosts[$index]}"
        IP="${ips[$index]}"
    fi
fi

if [ -z "$IP" ]; then
    echo "エラー: ${hostname} のIPアドレスがHostTable.csvに登録されていません"
    echo "setting/HostTable.csvを編集してから再度お試しください"
    sleep 3
    exit 1
fi

echo "RPi" "$hostname" "(" "$IP" ")" "をセットアップ/更新します"

#IP.txtへの書き込み

echo "RPi_ID=$hostname" > ~/setting/IP.txt
echo "IP=$IP" >> ~/setting/IP.txt

sleep 1

##SSH接続テスト

ssh2raspi $IP exit >/dev/null 2>&1

result=$?

if [ $result -ne 0 ]; then
    echo "エラー: Raspberry Pi との接続に失敗しました"

    sleep 30
    exit 1
fi

echo "Raspberry Pi との接続が完了しました"

sleep 2

##転送元(タブレット側)のRPiscriptsを確認

if [ ! -d ~/RPiscripts/script ]; then
    echo "エラー: ~/RPiscripts/script が見つかりません"
    echo "README記載の手順でリポジトリのスクリプトを取得・配置してください"
    sleep 5
    exit 1
fi

##実行内容の選択

result_mode=$(termux-dialog radio -v "初期セットアップ(パッケージインストール含む),スクリプト更新のみ" -t "実行内容を選んでください")
mode_index=$(echo "$result_mode" | jq -r '.index')

##script/フォルダの転送

echo "script/フォルダを転送します"

#既存のimageSetting.txtを退避(機体ごとの調整値を保持)
ssh2raspi $IP "[ -f script/imageSetting.txt ] && cp script/imageSetting.txt /tmp/imageSetting.txt.bak"

scp2raspi ~/RPiscripts/script "$user@$IP:~/"
scp2raspi ~/RPiscripts/VERSION "$user@$IP:~/"

#既存のimageSetting.txtを復元(新規セットアップ時は対象ファイルがないため何もしない)
ssh2raspi $IP "[ -f /tmp/imageSetting.txt.bak ] && cp /tmp/imageSetting.txt.bak script/imageSetting.txt && rm /tmp/imageSetting.txt.bak"

ssh2raspi $IP "chmod +x script/*.sh"

echo "script/フォルダの転送が完了しました"

sleep 1

##初期セットアップの場合のみ追加処理

if [ "$mode_index" == "0" ]; then
    echo "recordフォルダを作成します"
    ssh2raspi $IP "mkdir -p record"

    echo "必要なパッケージをインストールします(数分かかる場合があります)"
    ssh2raspi $IP "sudo apt update && sudo apt install -y python3-picamera2 rpicam-apps alsa-utils"

    echo "パッケージのインストールが完了しました"
fi

##VERSION表示

local_version=$(cat ~/RPiscripts/VERSION 2>/dev/null)
remote_version=$(ssh2raspi $IP "cat VERSION" 2>/dev/null)

echo "転送したRPiscripts VERSION: $local_version"
echo "RPi側に反映されたVERSION  : $remote_version"

sleep 5

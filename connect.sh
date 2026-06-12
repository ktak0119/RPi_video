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

    result=$(termux-dialog text -t "接続したいカメラのIDを入力してください" -i "例: UT01")
    hostname=$(echo "$result" | jq -r '.text')

    IP=$(awk -F',' -v h="$hostname" '$1==h {print $2}' ~/setting/HostTable.csv)

else
    option_list=$(IFS=,; echo "${hosts[*]}")
    option_list="${option_list},手動入力"

    result=$(termux-dialog radio -v "$option_list" -t "接続するRPiを選んでください")
    index=$(echo "$result" | jq -r '.index')

    if [ "$index" == "${#hosts[@]}" ]; then
        result=$(termux-dialog text -t "接続したいカメラのIDを入力してください" -i "例: UT01")
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

echo "RPi" "$hostname" "(" "$IP" ")" "と接続します"

##IP.txtへの書き込み(IPsearch.pyの代替)

echo "RPi_ID=$hostname" > ~/setting/IP.txt
echo "IP=$IP" >> ~/setting/IP.txt

sleep 1

##SSH接続テスト

ssh2raspi $IP exit >/dev/null 2>&1

result=$?

if [ $result -ne 0 ]; then
    echo "エラー: Raspberry Pi との接続に失敗しました"

    sleep 30
    exit 1 #スクリプトを中断してエラーコード1で終了
fi

echo "Raspberry Pi との接続が完了しました"

sleep 2

##SDカード容量のチェック

echo "Raspberry Piの容量をチェックします"

# SSHを使用してリモートサーバーに接続し、ストレージ容量を確認
total_space=$(ssh2raspi $IP df -h | awk '/\/dev\/root/ {print $2}')

# ストレージ容量を数値に変換（単位を除去）
total_space_num=$(echo "$total_space" | sed 's/G//' | awk -F. '{print $1}')

# 警告メッセージを表示
if [ "$total_space_num" -lt 10 ]; then
    echo "警告: カメラのストレージ容量が10GB未満です"

    #ファイル拡張の可否を尋ねる
    result_expansion=$(termux-dialog confirm -t "ストレージを拡張しますか?" -i "ファイル容量が制限されている可能性があります。\n ストレージを拡張した場合、再起動を実施します。")
    answer_expansion=$(echo "$result_expansion" | jq -r ".text")

    #yesの場合、raspi-configよりファイルを拡張
    if [ "$answer_expansion" != "yes" ]; then
        echo "ストレージを拡張せずプロセスを続けます"

    else
        echo "ストレージを拡張します"

        #コマンドからraspi-configを変更
        ssh2raspi $IP "sudo raspi-config nonint do_expand_rootfs"

        echo "ストレージの拡張を実施しました"

        echo "カメラを再起動します"

        ssh2raspi $IP "sudo reboot"

        sleep 5

        exit 0
    fi

else
    echo "カメラのストレージ容量は" "$total_space_num" " Gbです。"
fi

sleep 3

##接続設定とプレビュー

#プレビューに移るか否かの分岐

result_preview=$(termux-dialog confirm -t "プレビューを開始しますか?" -i "撮影中の確認の場合、Noを選んでください")
result_preview=$(echo "$result_preview" | jq -r '.text')

if [ "$result_preview" != "yes" ]; then
    echo "ウィンドウを閉じます"
    sleep 2
    exit 0
fi

echo "プレビューを開始します"

##現在時刻の確認とRPiへの時刻設定

now=$(date "+%Y%m%d%H%M%S")
now_disp=$(date "+%Y/%m/%d %H:%M:%S")

result_time=$(termux-dialog confirm -t "現在時刻の確認" -i "タブレットの現在時刻は\n${now_disp}\nです。\nこの時刻でRPiの時計を設定しますか?")
answer_time=$(echo "$result_time" | jq -r '.text')

if [ "$answer_time" != "yes" ]; then
    #時刻を手動入力
    result2=$(termux-dialog text -t "現在時刻を入力してください" -i "例：2023/5/15 11:05:00 -> 20230515110500" -n )
    now=$(echo "$result2" | jq -r '.text')
fi

# 桁数チェック
if [ ${#now} -ne 14 ]; then
    echo "Error: Invalid input length. Please provide a 14-digit input."
    sleep 2
    exit 1
fi

year=${now:0:4}
month=${now:4:2}
day=${now:6:2}
hour=${now:8:2}
minute=${now:10:2}
second=${now:12:2}

# 日付の妥当性チェック
if ! date -d "${year}-${month}-${day}" >/dev/null 2>&1; then
    echo "Error: Invalid date."
    sleep 2
    exit 1
fi

# 時刻の妥当性チェック
if ! date -d "${hour}:${minute}:${second}" >/dev/null 2>&1; then
    echo "Error: Invalid time."
    sleep 2
    exit 1
fi

formatted_date="${year}-${month}-${day} ${hour}:${minute}:${second}"

echo "カメラの時刻を以下に設定します"
echo "$formatted_date"

ssh2raspi $IP "sudo date --set=\"$formatted_date\"" #set Rpi clock

##プレビューの開始

ssh2raspi $IP "bash script/preview_start.sh"

#move to browser

URL="http://${IP}:8080/stream.mjpg"

echo "プレビューを開始します。5秒後に" "$URL" "に移行します"

sleep 5

termux-open "$URL"

##VERSION表示

local_version=$(cat ~/setting/VERSION 2>/dev/null)
remote_version=$(ssh2raspi $IP "cat VERSION" 2>/dev/null)

echo "タブレット側スクリプト VERSION: $local_version"
echo "RPi側スクリプト VERSION: $remote_version"

sleep 5

#!/bin/bash

#IPアドレスとポートの設定
source ~/setting/IP.txt
source ~/setting/sshSetting.txt	
source .bashrc

echo "IP" "$IP"

PORT="22"

#recordフォルダ内のデータの表示

echo "カメラ内のデータを表示します"

ssh2raspi $IP "ls record/*/ -lh -d"

#sleep 5

# フォルダリストを取得し、カンマ区切りの文字列に変換
folder_list=$(ssh2raspi $IP "ls -d record/*/")

# 改行文字で分割してディレクトリ名を抽出
dir_names=""
while read -r line; do
  dir_name=$(basename "$line")
  dir_names="$dir_names,$dir_name"
done <<< "$folder_list"

# 先頭のカンマを削除
dir_names="${dir_names#,}"

#echo "$dir_names"


# ダイアログボックスを表示
result_folder=$(termux-dialog checkbox -v "$dir_names" -t '確認するフォルダを選んでください')
result_folder=$(echo "$result_folder" | jq -r '.text' | sed 's/\[\(.*\)\]/\1/')

echo "$result_folder を開きます"

ssh2raspi $IP "ls \"record/$result_folder\" -lh"

sleep 5

#サムネイルのダウンロード
result_download=$(termux-dialog confirm -t "サムネイルのダウンロードを開始しますか？" -i "ダウンロードには時間がかかる場合があります")
answer_download=$(echo "$result_download" | jq -r '.text')

if [ "$answer_download" == "yes" ]; then
    echo "サムネイルのダウンロードを開始します"
    
    sleep 1
    
    #ディレクトリの作成
    local_directory="$HOME/storage/downloads/$result_folder"

    if [ ! -d "$local_directory" ]; then
        mkdir -p "$local_directory"
    fi

    #サムネイルのダウンロード
    ssh2raspi $IP "cd record/$result_folder && tar -czf - *.jpg | tar -xzf - -C $local_directory"

    echo "ダウンロードが完了しました"
    sleep 1

else
    echo "サムネイルのダウンロードをキャンセルしました"

fi

#データの削除

result_rm1=$(termux-dialog confirm -t "カメラ内のデータを削除しますか?" -i "バックアップを取ったか確認してください")
answer_rm1=$(echo "$result_rm1" | jq -r ".text")

if [ "$answer_rm1" != "yes" ]; then

    echo "削除がキャンセルされました"

else
    #二重のチェック
    result_rm2=$(termux-dialog confirm -t "本当にカメラ内のデータを削除しますか?" -i "削除すると復元ができませんのでご注意ください")
    answer_rm2=$(echo "$result_rm2" | jq -r ".text")

    if [ "$answer_rm2" != "yes" ]; then
        echo "削除がキャンセルされました"

    else
        echo "カメラ内のデータを削除します"
        sleep 1

        #recordフォルダごと削除し、新たにrecordフォルダを生成
        ssh2raspi $IP "sudo rm record -r"
        ssh2raspi $IP "mkdir record"

        echo "カメラ内のデータを削除しました"

    fi

fi

exit 0

#!/bin/bash

#IPアドレスの読み込み
source ~/setting/IP.txt
source ~/setting/sshSetting.txt
source .bashrc

echo "IP" "$IP"

echo "カメラを初期化しています"

#カメラの動作確認

#プレビューの停止
ssh2raspi $IP "bash script/preview_stop.sh"

sleep 3
echo "カメラを初期化しました"

sleep 2

##二重起動チェック

is_recording=$(ssh2raspi $IP "pid=\$(cat record/.recording.pid 2>/dev/null); if [ -n \"\$pid\" ] && ps -p \$pid > /dev/null 2>&1; then echo yes; else echo no; fi")

if [ "$is_recording" == "yes" ]; then
    echo "エラー: 既に撮影中のプロセスが存在します。"
    echo "撮影を終了してから再度実行してください。"
    sleep 5
    exit 1
fi

echo "カメラの起動テストを開始します"


# Raspberry PiにSSH接続してカメラの起動テスト
ssh2raspi $IP "rpicam-jpeg -o record/test.jpg -t 1000 -n"

# テスト画像の確認
if ssh2raspi $IP "[ -f \"record/test.jpg\" ]"; then

    #テスト画像の削除
    ssh2raspi $IP "sudo rm record/test.jpg"
    echo "カメラの起動テストが成功しました。"

else
    echo "エラー: カメラの起動テストに失敗しました。"
    sleep 3
    # 起動に失敗した場合、プロセスを中断
    exit 1
fi

##情報の入力

#対象名の入力
result_object=$(termux-dialog text -t "撮影対象を入力してください" -i "フォルダ名に使用します。対象種、集団 etc.")
object=$(echo "$result_object" | jq -r ".text")

#フォルダ名に重複がないかをチェック
dirs=$(ssh2raspi $IP "ls record")

#echo "$dirs が検出されました"

today=$(date "+%Y%m%d")

while [[ "$dirs" =~ "${today}_${object}" ]]; do

    echo "同名のフォルダが存在します。別の対象名を入力してください"

    #再入力
    result_object=$(termux-dialog text -t "撮影対象を入力してください" -i "フォルダ名に使用します。対象種、集団 etc.")
    object=$(echo "$result_object" | jq -r ".text")
done

#フォルダの作成
#echo "撮影データのフォルダを作成します"

ssh2raspi $IP "mkdir -p record/${today}_${object}"

echo "撮影データは record/""$today""_""$object""フォルダ内に生成されます"


#メタデータの入力
result_metadata=$(termux-dialog text -t "メタデータを入力してください" -i "撮影に関する情報をメモとして残すことができます\n 例：撮影場所、撮影者、対象種の詳細、天気等")
metadata=$(echo "$result_metadata" | jq -r ".text")

ssh2raspi $IP "touch record/${today}_${object}/memo.txt"
ssh2raspi $IP "echo "$metadata" > record/${today}_${object}/memo.txt"
ssh2raspi $IP "echo \"RPi_ID=${RPi_ID}\" >> record/${today}_${object}/memo.txt"

echo "memo.txtファイルにデータを書き込みました"

#exit 1

##音声の同時録音確認

result_audio=$(termux-dialog confirm -t "音声も録音しますか?" -i "USBマイクが接続されている必要があります")
answer_audio=$(echo "$result_audio" | jq -r ".text")

if [ "$answer_audio" == "yes" ]; then
    echo "音声付きで撮影します"
    AUDIO_FLAG="--audio"
else
    echo "音声なしで撮影します"
    AUDIO_FLAG=""
fi

##撮影の開始


echo "撮影を開始します"

#撮影コマンド
ssh2raspi $IP "nohup python3 script/startRecording.py 'record/${today}_${object}' $AUDIO_FLAG > 'record/${today}_${object}/out.log' 2> 'record/${today}_${object}/error.log' &"



#check recording
sleep 5
ssh2raspi $IP "ls record/${today}_${object} -l -t | head -n 2"
sleep 3
ssh2raspi $IP "ls record/${today}_${object} -l -t | head -n 2"

echo "動画ファイルのサイズを確認し、問題なければウィンドウを閉じてください"


sleep 15

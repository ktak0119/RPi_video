#!/bin/bash

#IPアドレスの読み込み
source ~/setting/IP.txt
source ~/setting/sshSetting.txt
source .bashrc

echo "IP" "$IP"

# オプションと設定ファイルのパス
options=("width" "height" "framerate" "bitrate" "video_duration" "video_number" "audio_device")
setting_file="script/imageSetting.txt"

echo "現在の設定は以下のとおりです"

ssh2raspi $IP "cat $setting_file"

#sleep 5

# ダイアログボックスを表示し、ユーザーからの選択を受け取る
result_var=$(termux-dialog checkbox -v "$(IFS=,; echo "${options[*]}")" -t '変更する変数を選択してください')
option=$(echo "$result_var" | jq -r '.text' | sed 's/\[\(.*\)\]/\1/')

echo "$option を変更します"

# 変更後の値を入力(audio_deviceのみ文字列入力、それ以外は数値入力)
if [ "$option" == "audio_device" ]; then
    result_val=$(termux-dialog text -t "変更後の値を入力してください" -i "USBマイクのALSAデバイス名を入力 (例: plughw:1,0)")
else
    result_val=$(termux-dialog text -t "入力可能な範囲を確認して入力してください" -i "変更後の値を入力" -n)
fi
value=$(echo "$result_val" | jq -r ".text")

#echo "$value"

# 制約条件をチェック
case "$option" in
  "width")
    if ((value >= 1 && value <= 2400)); then
      echo "widthの値は設定範囲内です"
    else
      echo "widthの値が設定範囲外です。1から2400の範囲で設定してください。"
      exit 1
    fi
    ;;
  "height")
    if ((value >= 1 && value <= 2400)); then
      echo "heightの値は設定範囲内です"
    else
      echo "heightの値が設定範囲外です。1から2400の範囲で設定してください。"
      exit 1
    fi
    ;;
  "framerate")
    if ((value >= 1 && value <= 40)); then
      echo "framerateの値は設定範囲内です"
    else
      echo "framerateの値が設定範囲外です。1から40の範囲で設定してください。"
      exit 1
    fi
    ;;
  "bitrate")
    if ((value >= 100000 && value <= 25000000)); then
      echo "bitrateの値は設定範囲内です"
    else
      echo "bitrateの値が設定範囲外です。100000から25000000(bps)の範囲で設定してください。"
      exit 1
    fi
    ;;
  "video_duration")
    if ((value >= 1 && value <= 3600)); then
      echo "video_durationの値は設定範囲内です"
    else
      echo "video_durationの値が設定範囲外です。1から3600の範囲で設定してください。"
      exit 1
    fi
    ;;
  "video_number")
    if ((value >= 1 && value <= 1000)); then
      echo "video_numberの値は設定範囲内です"
    else
      echo "video_numberの値が設定範囲外です。1から1000の範囲で設定してください。"
      exit 1
    fi
    ;;
  "audio_device")
    if [ -n "$value" ]; then
      echo "audio_deviceの値を更新します"
    else
      echo "audio_deviceの値が空です。デバイス名を入力してください。"
      exit 1
    fi
    ;;
  *)
    echo "無効なオプションが選択されました"
    exit 1
    ;;
esac

echo "$option=$value で設定を上書きします。"

ssh2raspi $IP "cp $setting_file $setting_file.bak"

# 新しい値で設定ファイルを更新
ssh2raspi $IP "sed -i 's/^$option=.*/$option=$value/' $setting_file"

echo "設定ファイルを更新しました"

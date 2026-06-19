#!/bin/bash
# 映像(.h264)と音声(.wav)を同名ファイルから1本のmp4に合成する。
# ラズパイ本体の処理ではなく、PC側でデータ吸い出し後に使うffmpegコマンド。
#
# 使い方: ./merge_video_audio.sh [-f fps] [-g gain_db] <base_name>
#   -f fps      撮影時のフレームレート（省略時 15。recording.py側の設定に合わせて指定する）
#   -g gain_db  音声の増幅量[dB]（省略時 50）
#   base_name   拡張子を除いた共通ファイル名
#               (<base_name>.h264 と <base_name>.wav から <base_name>.mp4 を生成)
#
# 例: ./merge_video_audio.sh -f 24 -g 60 /path/to/record/20260619_120000

set -e

FPS=15
GAIN_DB=50

usage() {
  echo "使い方: $0 [-f fps] [-g gain_db] <base_name>" >&2
  exit 1
}

while getopts "f:g:" opt; do
  case "$opt" in
    f) FPS="$OPTARG" ;;
    g) GAIN_DB="$OPTARG" ;;
    *) usage ;;
  esac
done
shift $((OPTIND - 1))

BASE_NAME="$1"
[ -z "$BASE_NAME" ] && usage

VIDEO_INPUT="${BASE_NAME}.h264"
AUDIO_INPUT="${BASE_NAME}.wav"
OUTPUT="${BASE_NAME}.mp4"

ffmpeg \
  -framerate "$FPS" -i "$VIDEO_INPUT" \
  -ss 6 -i "$AUDIO_INPUT" \
  -map 0:v:0 -map 1:a:0 \
  -c:v libx264 -r "$FPS" -pix_fmt yuv420p \
  -c:a aac -b:a 128k -ar 44100 -ac 1 \
  -af "volume=${GAIN_DB}dB,alimiter=limit=0.95" \
  -shortest "$OUTPUT"

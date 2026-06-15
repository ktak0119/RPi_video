import os
import re
import shutil
import socket
import subprocess
from datetime import datetime

from flask import Flask, Response, abort, redirect, render_template, request, send_from_directory, url_for

import camera_manager
import common

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SETTINGS_PATH = os.path.join(BASE_DIR, "imageSetting.txt")
RECORD_DIR = os.path.join(BASE_DIR, "..", "record")
RPI_ID = socket.gethostname()

app = Flask(__name__)
manager = camera_manager.CameraManager(SETTINGS_PATH)

# key, ラベル, 単位, 最小値, 最大値, 説明
SETTINGS_FIELDS = [
    ("width", "横解像度", "px", 1, 2400, "動画の横解像度"),
    ("height", "縦解像度", "px", 1, 2400, "動画の縦解像度"),
    ("framerate", "フレームレート", "fps", 1, 40, "1秒あたりのフレーム数"),
    ("bitrate", "ビットレート", "bps", 100000, 25000000, "映像のビットレート(画質に影響)"),
    ("video_duration", "1ファイルの撮影時間", "秒", 1, 3600, "1つの動画ファイルあたりの撮影時間"),
    ("video_number", "撮影ファイル数の上限", "個", 1, 1000, "1回の撮影で作成するファイル数の上限"),
]

# 停止スタック後に孤立しうる録画用プロセス
RESET_PROCESS_NAMES = ("rpicam-vid", "rpicam-jpeg", "arecord")

DATETIME_RE = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$")


def read_version(path):
    try:
        with open(path) as f:
            return f.read().strip()
    except FileNotFoundError:
        return "unknown"


@app.route("/")
def index():
    status = manager.get_status()
    folder_name = os.path.basename(status["record_dir"]) if status["record_dir"] else None
    return render_template(
        "index.html",
        status=status,
        folder_name=folder_name,
        rpi_version=read_version(os.path.join(BASE_DIR, "..", "VERSION")),
    )


@app.route("/preview")
def preview():
    status = manager.get_status()
    if status["state"] == camera_manager.STATE_RECORDING:
        return render_template("preview.html", available=False, error="撮影中はプレビューを利用できません")

    ok, error = manager.start_preview()
    if not ok:
        return render_template("preview.html", available=False, error=error)

    return render_template("preview.html", available=True, error=None)


@app.route("/stream.mjpg")
def stream_mjpg():
    if manager.get_status()["state"] != camera_manager.STATE_PREVIEW:
        return "プレビューが開始されていません", 409

    def generate():
        while True:
            frame = manager.next_frame()
            if frame is None:
                break
            yield b"--FRAME\r\n"
            yield b"Content-Type: image/jpeg\r\n"
            yield f"Content-Length: {len(frame)}\r\n\r\n".encode()
            yield frame
            yield b"\r\n"

    return Response(generate(), mimetype="multipart/x-mixed-replace; boundary=FRAME")


@app.route("/record", methods=["GET", "POST"])
def record():
    status = manager.get_status()
    if status["state"] == camera_manager.STATE_RECORDING:
        return render_template("record.html", busy=True, error=None)

    error = None
    if request.method == "POST":
        object_name = request.form.get("object_name", "").strip()
        metadata = request.form.get("metadata", "").strip()
        audio = request.form.get("audio") == "on"

        if not object_name:
            error = "撮影対象名を入力してください"
        else:
            today = datetime.now().strftime("%Y%m%d")
            folder_name = f"{today}_{object_name}"
            record_dir = os.path.join(RECORD_DIR, folder_name)

            if os.path.exists(record_dir):
                error = f"フォルダ「{folder_name}」は既に存在します。別の対象名を入力してください"
            else:
                os.makedirs(record_dir)
                with open(os.path.join(record_dir, "memo.txt"), "w") as f:
                    f.write(metadata + "\n")
                    f.write(f"RPi_ID={RPI_ID}\n")

                ok, start_error = manager.start_recording(record_dir, audio)
                if ok:
                    return redirect(url_for("index"))
                error = start_error

    return render_template("record.html", busy=False, error=error)


@app.route("/record/stop", methods=["POST"])
def record_stop():
    manager.stop_recording()
    return redirect(url_for("index"))


@app.route("/settings", methods=["GET", "POST"])
def settings():
    current = common.load_settings(SETTINGS_PATH)
    errors = {}
    success = False

    if request.method == "POST":
        values = {}
        for key, label, unit, min_val, max_val, desc in SETTINGS_FIELDS:
            raw = request.form.get(key, "").strip()
            try:
                num = int(raw)
                if not (min_val <= num <= max_val):
                    raise ValueError
            except ValueError:
                errors[key] = f"{min_val}から{max_val}の範囲の整数で入力してください"
                values[key] = raw
            else:
                values[key] = str(num)

        audio_device = request.form.get("audio_device", "").strip()
        if not audio_device:
            errors["audio_device"] = "ALSAデバイス名を入力してください"
        values["audio_device"] = audio_device

        current = values
        if not errors:
            common.save_settings(SETTINGS_PATH, values)
            success = True

    return render_template(
        "settings.html",
        fields=SETTINGS_FIELDS,
        current=current,
        errors=errors,
        success=success,
    )


def _recording_path(folder):
    if not os.path.isdir(RECORD_DIR) or folder not in os.listdir(RECORD_DIR):
        abort(404)
    path = os.path.join(RECORD_DIR, folder)
    if not os.path.isdir(path):
        abort(404)
    return path


@app.route("/data")
def data():
    recordings = common.list_recordings(RECORD_DIR)
    return render_template("data.html", recordings=recordings, human_size=common.human_size)


@app.route("/data/<folder>")
def data_detail(folder):
    _recording_path(folder)
    files, memo = common.get_recording_files(RECORD_DIR, folder)
    return render_template(
        "data_detail.html", folder=folder, files=files, memo=memo, human_size=common.human_size, error=None
    )


@app.route("/data/<folder>/file/<filename>")
def data_file(folder, filename):
    record_dir = _recording_path(folder)
    return send_from_directory(record_dir, filename)


@app.route("/data/<folder>/delete", methods=["POST"])
def data_delete(folder):
    record_dir = _recording_path(folder)

    status = manager.get_status()
    if status["record_dir"] and os.path.abspath(status["record_dir"]) == os.path.abspath(record_dir):
        files, memo = common.get_recording_files(RECORD_DIR, folder)
        return render_template(
            "data_detail.html",
            folder=folder,
            files=files,
            memo=memo,
            human_size=common.human_size,
            error="撮影中のフォルダは削除できません",
        )

    shutil.rmtree(record_dir)
    return redirect(url_for("data"))


def _render_system(error=None, message=None):
    return render_template(
        "system.html",
        status=manager.get_status(),
        rpi_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        error=error,
        message=message,
    )


@app.route("/system")
def system_page():
    return _render_system()


@app.route("/system/reset_camera", methods=["POST"])
def reset_camera():
    if manager.get_status()["state"] == camera_manager.STATE_RECORDING:
        return _render_system(error="撮影中はリセットできません")

    for name in RESET_PROCESS_NAMES:
        subprocess.run(["pkill", "-9", "-f", name])

    return _render_system(message="カメラプロセスをリセットしました")


@app.route("/system/reboot", methods=["POST"])
def reboot():
    if manager.get_status()["state"] == camera_manager.STATE_RECORDING:
        return _render_system(error="撮影中は実行できません")

    subprocess.run(["sudo", "shutdown", "-r", "+1"])
    return _render_system(message="1分後に再起動します")


@app.route("/system/shutdown", methods=["POST"])
def shutdown():
    if manager.get_status()["state"] == camera_manager.STATE_RECORDING:
        return _render_system(error="撮影中は実行できません")

    subprocess.run(["sudo", "shutdown", "-h", "+1"])
    return _render_system(message="1分後にシャットダウンします")


@app.route("/system/cancel_shutdown", methods=["POST"])
def cancel_shutdown():
    subprocess.run(["sudo", "shutdown", "-c"])
    return _render_system(message="再起動/シャットダウンの予約を取り消しました")


@app.route("/system/set_time", methods=["POST"])
def set_time():
    if manager.get_status()["state"] == camera_manager.STATE_RECORDING:
        return _render_system(error="撮影中は実行できません")

    value = request.form.get("datetime", "").strip()
    if not DATETIME_RE.match(value):
        return _render_system(error="時刻の形式が不正です")

    subprocess.run(["sudo", "date", "--set=" + value])
    return _render_system(message=f"RPiの時計を{value}に設定しました")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, threaded=True)

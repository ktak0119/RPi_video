import os
import socket
from datetime import datetime

from flask import Flask, Response, redirect, render_template, request, url_for

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
        tablet_version=read_version(os.path.join(BASE_DIR, "..", "..", "VERSION")),
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


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, threaded=True)

import os
import socket
from datetime import datetime

from flask import Flask, Response, redirect, render_template, request, url_for

import camera_manager

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SETTINGS_PATH = os.path.join(BASE_DIR, "imageSetting.txt")
RECORD_DIR = os.path.join(BASE_DIR, "..", "record")
RPI_ID = socket.gethostname()

app = Flask(__name__)
manager = camera_manager.CameraManager(SETTINGS_PATH)


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


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)

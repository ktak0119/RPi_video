import os
import subprocess
import traceback
from datetime import datetime

import common


def shoot_thumbnail(jpg_path, width, height):
    subprocess.run([
        "rpicam-jpeg", "-o", jpg_path, "-t", "1000", "-n",
        "--width", width, "--height", height,
    ])


def start_audio(wav_path, duration, audio_device):
    return subprocess.Popen([
        "arecord", "-D", audio_device,
        "-f", "S16_LE", "-c", "1", "-r", "44100",
        "-d", str(duration), wav_path,
    ])


def record_video(h264_path, width, height, framerate, bitrate, duration):
    subprocess.run([
        "rpicam-vid", "-t", str(duration * 1000), "-o", h264_path, "-n",
        "--width", width, "--height", height,
        "--framerate", framerate, "--bitrate", bitrate,
    ])


def run_recording_loop(record_dir, audio, stop_event, settings_path):
    settings = common.load_settings(settings_path)
    width = settings["width"]
    height = settings["height"]
    framerate = settings["framerate"]
    bitrate = settings["bitrate"]
    duration = int(settings["video_duration"])
    audio_device = settings.get("audio_device", "plughw:1,0")
    video_number = int(settings["video_number"])

    for seq in range(1, video_number + 1):
        if stop_event.is_set():
            break
        try:
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            base = common.make_basename(record_dir, seq, timestamp)
            jpg_path = os.path.join(record_dir, base + ".jpg")
            h264_path = os.path.join(record_dir, base + ".h264")
            wav_path = os.path.join(record_dir, base + ".wav")

            shoot_thumbnail(jpg_path, width, height)

            audio_proc = None
            if audio:
                audio_proc = start_audio(wav_path, duration, audio_device)

            record_video(h264_path, width, height, framerate, bitrate, duration)

            if audio_proc is not None:
                audio_proc.wait()
        except Exception:
            traceback.print_exc()

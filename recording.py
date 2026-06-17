import os
import subprocess
import time
import traceback
from datetime import datetime

import common


def shoot_thumbnail(jpg_path, width, height):
    subprocess.run([
        "rpicam-jpeg", "-o", jpg_path, "-t", "1000", "-n",
        "--width", width, "--height", height,
    ])


def start_audio(wav_path, duration, audio_device, handle):
    proc = subprocess.Popen([
        "arecord", "-D", audio_device,
        "-f", "S16_LE", "-c", "1", "-r", "44100",
        "-d", str(duration), wav_path,
    ])
    handle.register(proc)
    return proc


def record_video(h264_path, width, height, framerate, bitrate, duration, handle):
    from picamera2 import Picamera2, MappedArray
    from picamera2.encoders import H264Encoder
    from picamera2.outputs import FileOutput
    import cv2

    frame_count = 0
    fps_label = f"{int(framerate)}fps"
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = max(0.5, int(width) / 1600)
    thickness = 2

    def pre_callback(request):
        nonlocal frame_count
        frame_count += 1
        text = (
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            + f"  {fps_label}  #{frame_count:06d}"
        )
        with MappedArray(request, "main") as m:
            (tw, th), _ = cv2.getTextSize(text, font, font_scale, thickness)
            cv2.rectangle(m.array, (8, 8), (tw + 12, th + 16), (0, 0, 0), -1)
            cv2.putText(m.array, text, (10, th + 12), font, font_scale, (255, 255, 255), thickness)

    picam2 = Picamera2()
    try:
        config = picam2.create_video_configuration(
            main={"size": (int(width), int(height))},
            controls={"FrameRate": int(framerate)},
        )
        picam2.configure(config)
        picam2.pre_callback = pre_callback
        encoder = H264Encoder(bitrate=int(bitrate))
        picam2.start_recording(encoder, FileOutput(h264_path))
        deadline = time.monotonic() + duration
        while time.monotonic() < deadline:
            if handle.stop_event.is_set():
                break
            time.sleep(0.1)
    finally:
        picam2.stop_recording()
        picam2.close()


def run_recording_loop(record_dir, audio, handle, settings_path):
    settings = common.load_settings(settings_path)
    width = settings["width"]
    height = settings["height"]
    framerate = settings["framerate"]
    bitrate = settings["bitrate"]
    duration = int(settings["video_duration"])
    audio_device = settings.get("audio_device", "plughw:1,0")
    video_number = int(settings["video_number"])

    for seq in range(1, video_number + 1):
        if handle.stop_event.is_set():
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
                audio_proc = start_audio(wav_path, duration, audio_device, handle)

            record_video(h264_path, width, height, framerate, bitrate, duration, handle)

            if audio_proc is not None:
                audio_proc.wait()
                handle.unregister(audio_proc)
        except Exception:
            traceback.print_exc()

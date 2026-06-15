import io
import logging
import threading
from threading import Condition

STATE_IDLE = "idle"
STATE_PREVIEW = "preview"
STATE_RECORDING = "recording"


class StreamingOutput(io.BufferedIOBase):
    def __init__(self):
        self.frame = None
        self.condition = Condition()

    def write(self, buf):
        with self.condition:
            self.frame = buf
            self.condition.notify_all()


class CameraManager:
    """picamera2(プレビュー)とrpicam-vid/rpicam-jpeg(録画)の排他制御を行う。

    picamera2はlibcameraを掴んでいる間、rpicam-vid/rpicam-jpegを実行できないため、
    録画開始時にプレビュー用のPicamera2インスタンスを解放してから録画用サブプロセスを起動する。
    """

    def __init__(self, settings_path):
        self.settings_path = settings_path
        self.lock = threading.Lock()
        self.state = STATE_IDLE
        self.picam2 = None
        self.output = None
        self.record_dir = None
        self.stop_event = None

    def get_status(self):
        with self.lock:
            return {"state": self.state, "record_dir": self.record_dir}

    def start_preview(self):
        with self.lock:
            if self.state == STATE_RECORDING:
                return False, "撮影中はプレビューを開始できません"
            if self.state == STATE_PREVIEW:
                return True, None

            try:
                from picamera2 import Picamera2
                from picamera2.encoders import MJPEGEncoder
                from picamera2.outputs import FileOutput

                output = StreamingOutput()
                picam2 = Picamera2()
                picam2.configure(picam2.create_video_configuration(main={"size": (640, 480)}))
                picam2.start_recording(MJPEGEncoder(), FileOutput(output))
            except Exception as e:
                return False, f"カメラの初期化に失敗しました: {e}"

            self.picam2 = picam2
            self.output = output
            self.state = STATE_PREVIEW
            return True, None

    def next_frame(self):
        output = self.output
        if output is None:
            return None
        with output.condition:
            output.condition.wait(timeout=5)
            return output.frame

    def start_recording(self, record_dir, audio):
        with self.lock:
            if self.state == STATE_RECORDING:
                return False, "既に撮影中です"
            self._stop_preview_locked()

            stop_event = threading.Event()
            self.stop_event = stop_event
            self.record_dir = record_dir
            self.state = STATE_RECORDING

        thread = threading.Thread(
            target=self._run_recording, args=(record_dir, audio, stop_event), daemon=True
        )
        thread.start()
        return True, None

    def stop_recording(self):
        with self.lock:
            if self.state != STATE_RECORDING or self.stop_event is None:
                return False
            self.stop_event.set()
            return True

    def _run_recording(self, record_dir, audio, stop_event):
        import recording

        try:
            recording.run_recording_loop(record_dir, audio, stop_event, self.settings_path)
        except Exception:
            logging.exception("recording loop failed")
        finally:
            with self.lock:
                self.state = STATE_IDLE
                self.record_dir = None
                self.stop_event = None

    def _stop_preview_locked(self):
        if self.state != STATE_PREVIEW:
            return
        self.picam2.stop_recording()
        self.picam2.close()
        self.picam2 = None
        self.output = None
        self.state = STATE_IDLE

import io
import logging
import signal
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


class RecordingHandle:
    """録画ループの停止指示と、実行中のrpicam-vid/arecordプロセスの管理を行う。

    rpicam-vid/arecordは指定したdurationが終わるまで動き続けるため、
    stop()で実行中のプロセスにSIGINTを送り、Ctrl-Cと同様に即座に終了させる。
    """

    def __init__(self):
        self.stop_event = threading.Event()
        self._procs = []
        self._procs_lock = threading.Lock()

    def register(self, proc):
        with self._procs_lock:
            self._procs.append(proc)

    def unregister(self, proc):
        with self._procs_lock:
            if proc in self._procs:
                self._procs.remove(proc)

    def stop(self):
        self.stop_event.set()
        with self._procs_lock:
            procs = list(self._procs)
        for proc in procs:
            if proc.poll() is None:
                try:
                    proc.send_signal(signal.SIGINT)
                except ProcessLookupError:
                    pass


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
        self.recording_handle = None

    def get_status(self):
        with self.lock:
            stopping = (
                self.state == STATE_RECORDING
                and self.recording_handle is not None
                and self.recording_handle.stop_event.is_set()
            )
            return {"state": self.state, "record_dir": self.record_dir, "stopping": stopping}

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

            picam2_to_release = None
            if self.state == STATE_PREVIEW:
                picam2_to_release = self.picam2
                self.picam2 = None
                self.output = None

            handle = RecordingHandle()
            thread = threading.Thread(
                target=self._run_recording,
                args=(record_dir, audio, handle, picam2_to_release),
                daemon=True,
            )
            self.recording_handle = handle
            self.record_dir = record_dir
            self.state = STATE_RECORDING

        thread.start()
        return True, None

    def stop_recording(self):
        with self.lock:
            if self.state != STATE_RECORDING or self.recording_handle is None:
                return False
            handle = self.recording_handle
        handle.stop()
        return True

    def _run_recording(self, record_dir, audio, handle, picam2_to_release):
        if picam2_to_release is not None:
            try:
                picam2_to_release.stop_recording()
                picam2_to_release.close()
            except Exception:
                logging.exception("failed to release preview camera")

        import recording

        try:
            recording.run_recording_loop(record_dir, audio, handle, self.settings_path)
        except Exception:
            logging.exception("recording loop failed")
        finally:
            with self.lock:
                self.state = STATE_IDLE
                self.record_dir = None
                self.recording_handle = None

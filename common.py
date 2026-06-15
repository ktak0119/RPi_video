import os
import shutil


def load_settings(path="script/imageSetting.txt"):
    settings = {}
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            key, value = line.split("=", 1)
            settings[key.strip()] = value.strip()
    return settings


SETTINGS_KEY_ORDER = (
    "width",
    "height",
    "framerate",
    "bitrate",
    "video_duration",
    "video_number",
    "audio_device",
)


def save_settings(path, settings):
    try:
        shutil.copyfile(path, path + ".bak")
    except FileNotFoundError:
        pass

    with open(path, "w") as f:
        for key in SETTINGS_KEY_ORDER:
            f.write(f"{key}={settings[key]}\n")


def make_basename(record_dir, seq, timestamp):
    folder_name = record_dir.rstrip("/").split("/")[-1]
    return f"{folder_name}_{seq:04d}_{timestamp}"


def human_size(num_bytes):
    size = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.1f}{unit}" if unit != "B" else f"{int(size)}{unit}"
        size /= 1024


def list_recordings(record_dir):
    if not os.path.isdir(record_dir):
        return []

    recordings = []
    for name in sorted(os.listdir(record_dir), reverse=True):
        path = os.path.join(record_dir, name)
        if not os.path.isdir(path):
            continue

        files = os.listdir(path)
        total_size = sum(os.path.getsize(os.path.join(path, f)) for f in files)
        thumbnail = next((f for f in sorted(files) if f.lower().endswith(".jpg")), None)

        recordings.append({
            "name": name,
            "file_count": len(files),
            "total_size": total_size,
            "thumbnail": thumbnail,
        })

    return recordings


def get_recording_files(record_dir, folder):
    path = os.path.join(record_dir, folder)

    files = []
    memo = ""
    for name in sorted(os.listdir(path)):
        if name == "memo.txt":
            with open(os.path.join(path, name)) as f:
                memo = f.read()
            continue
        files.append({
            "name": name,
            "size": os.path.getsize(os.path.join(path, name)),
            "is_image": name.lower().endswith(".jpg"),
        })

    return files, memo

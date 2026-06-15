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

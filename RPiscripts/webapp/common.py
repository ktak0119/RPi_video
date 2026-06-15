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


def make_basename(record_dir, seq, timestamp):
    folder_name = record_dir.rstrip("/").split("/")[-1]
    return f"{folder_name}_{seq:04d}_{timestamp}"

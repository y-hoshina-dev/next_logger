import os
import csv
import json
from datetime import datetime

def generate_log_filename(product, serial, comment, ext):
    today = datetime.now().strftime("%Y%m%d")
    parts = [product, serial, comment, today]
    name = "_".join(filter(None, parts))
    return f"{name}.{ext}"

def write_csv(file_path, timestamp, data):
    file_exists = os.path.isfile(file_path)
    with open(file_path, "a", newline='', encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["Timestamp", "Data"])
        writer.writerow([timestamp, data])

def write_json(file_path, timestamp, data):
    log_entry = {"timestamp": timestamp, "data": data}
    if os.path.isfile(file_path):
        with open(file_path, "r+", encoding="utf-8") as f:
            logs = json.load(f)
            logs.append(log_entry)
            f.seek(0)
            json.dump(logs, f, indent=2)
    else:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump([log_entry], f, indent=2)

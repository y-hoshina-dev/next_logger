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
    entry = {"timestamp": timestamp, "data": data}
    if os.path.isfile(file_path):
        with open(file_path, "r+", encoding="utf-8") as f:
            try:
                logs = json.load(f)
            except json.JSONDecodeError:
                logs = []
            logs.append(entry)
            f.seek(0)
            json.dump(logs, f, indent=2)
    else:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump([entry], f, indent=2)

def write_txt(file_path, timestamp, data):
    with open(file_path, "a", encoding="utf-8") as f:
        f.write(f"{timestamp}: {data}\n")

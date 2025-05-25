import os
import json
import csv

def create_filename(info, ext):
    name = f"{info['product']}_{info['serial']}"
    if info['comment']:
        name += f"_{info['comment']}"
    name += f"_{info['date']}.{ext}"
    return os.path.join(info['save_dir'], name)

def write_log(info, timestamp, data, format):
    if format == "txt":
        filename = create_filename(info, "txt")
        with open(filename, "a", encoding="utf-8") as f:
            f.write(f"{timestamp}: {data}\n")
    elif format == "csv":
        filename = create_filename(info, "csv")
        with open(filename, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([timestamp, data])
    elif format == "json":
        filename = create_filename(info, "json")
        entry = {"timestamp": timestamp, "data": data}
        if os.path.exists(filename):
            with open(filename, "r+", encoding="utf-8") as f:
                logs = json.load(f)
                logs.append(entry)
                f.seek(0)
                json.dump(logs, f, indent=2, ensure_ascii=False)
        else:
            with open(filename, "w", encoding="utf-8") as f:
                json.dump([entry], f, indent=2, ensure_ascii=False)

def write_error_log(save_dir, timestamp, data):
    error_file = os.path.join(save_dir, "error_log.txt")
    with open(error_file, "a", encoding="utf-8") as f:
        f.write(f"{timestamp}: {data}\n")

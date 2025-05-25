import os
from datetime import datetime

def get_log_file_path():
    os.makedirs("logs", exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return os.path.join("logs", f"log_{timestamp}.txt")

def write_log(file_path, data):
    with open(file_path, "a", encoding="utf-8") as f:
        f.write(data + "\n")

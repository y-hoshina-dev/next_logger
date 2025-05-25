# logger/file_writer.py

def write_log(file_path, data):
    with open(file_path, "a", encoding="utf-8") as f:
        f.write(data + "\n")

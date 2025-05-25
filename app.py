import tkinter as tk
from tkinter import ttk, filedialog
import serial
import threading
import time
from datetime import datetime
import os
from logger.file_writer import write_log, write_error_log
from logger.gui_components import create_gui


# グローバル制御フラグ
is_logging = False
is_paused = False

def read_serial(port, baudrate, log_format, file_info, status_label, log_output):
    global is_logging, is_paused
    timestamp_format = "%Y-%m-%d %H:%M:%S"
    try:
        ser = serial.Serial(port, baudrate, timeout=1)
        status_label.config(text="接続中...")
        while is_logging:
            if is_paused:
                time.sleep(0.1)
                continue
            if ser.in_waiting:
                data = ser.readline().decode("utf-8", errors="ignore").strip()
                timestamp = datetime.now().strftime(timestamp_format)
                log_output.insert(tk.END, f"{timestamp}: {data}\n")
                log_output.see(tk.END)
                write_log(file_info, timestamp, data, log_format)
                if "ERROR" in data or "NG" in data:
                    write_error_log(file_info["save_dir"], timestamp, data)
        ser.close()
        status_label.config(text="停止しました")
    except serial.SerialException as e:
        status_label.config(text=f"エラー: {e}")

def start_logging(port_var, baud_var, format_var, file_info, status_label, log_output):
    global is_logging
    if is_logging:
        return
    is_logging = True
    t = threading.Thread(target=read_serial, args=(
        port_var.get(),
        int(baud_var.get()),
        format_var.get(),
        file_info,
        status_label,
        log_output
    ))
    t.daemon = True
    t.start()
    status_label.config(text="ログ取得中...")

def stop_logging(status_label):
    global is_logging
    is_logging = False
    status_label.config(text="停止中...")

def pause_logging(status_label):
    global is_paused
    is_paused = True
    status_label.config(text="⏸ 一時停止中")

def resume_logging(status_label):
    global is_paused
    is_paused = False
    status_label.config(text="▶️ 再開")

if __name__ == "__main__":
    root = tk.Tk()
    root.title("シリアルロガー GUI")
    create_gui(root, start_logging, stop_logging, pause_logging, resume_logging)
    root.mainloop()

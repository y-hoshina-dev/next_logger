import tkinter as tk
from tkinter import ttk, filedialog
from logger.serial_reader import open_serial_port, read_serial_data
from logger.file_writer import generate_log_filename, write_csv, write_json, write_txt
import serial.tools.list_ports
from datetime import datetime
import os

ser = None
is_logging = False
log_file_path = ""
log_format = "csv"
save_dir = ""

def get_serial_ports():
    return [p.device for p in serial.tools.list_ports.comports()]

def refresh_ports():
    ports = get_serial_ports()
    port_combo["values"] = ports
    if ports:
        port_var.set(ports[0])

def select_save_dir():
    global save_dir
    save_dir = filedialog.askdirectory()
    dir_label.config(text=save_dir if save_dir else "未選択")

def start_logging():
    global ser, is_logging, log_file_path, log_format

    if not save_dir:
        status_label.config(text="❗保存フォルダが未指定です")
        return

    product = product_var.get()
    serial = serial_var.get()
    comment = comment_var.get()
    log_format = format_var.get()
    filename = generate_log_filename(product, serial, comment, log_format)
    log_file_path = os.path.join(save_dir, filename)

    try:
        ser = open_serial_port(port_var.get(), int(baud_var.get()))
        if ser:
            is_logging = True
            status_label.config(text=f"✅ Logging to {filename}")
            root.after(100, read_loop)
        else:
            status_label.config(text="❌ ポートオープン失敗")
    except Exception as e:
        status_label.config(text=f"エラー: {e}")

def stop_logging():
    global is_logging
    is_logging = False
    if ser and ser.is_open:
        ser.close()
    status_label.config(text="⏹ 停止しました")

def read_loop():
    if is_logging and ser:
        data = read_serial_data(ser)
        if data:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_output.insert(tk.END, f"{timestamp}: {data}\n")
            log_output.see(tk.END)
            if log_format == "csv":
                write_csv(log_file_path, timestamp, data)
            elif log_format == "json":
                write_json(log_file_path, timestamp, data)
            elif log_format == "txt":
                write_txt(log_file_path, timestamp, data)
        root.after(100, read_loop)

# GUI構築
root = tk.Tk()
root.title("Serial Logger GUI")

frame = tk.Frame(root)
frame.pack(padx=10, pady=10)

tk.Label(frame, text="COMポート:").grid(row=0, column=0)
port_var = tk.StringVar()
port_combo = ttk.Combobox(frame, textvariable=port_var, width=10)
port_combo.grid(row=0, column=1)
tk.Button(frame, text="再スキャン", command=refresh_ports).grid(row=0, column=2)

tk.Label(frame, text="ボーレート:").grid(row=1, column=0)
baud_var = tk.StringVar(value="9600")
tk.Entry(frame, textvariable=baud_var, width=10).grid(row=1, column=1)

tk.Label(frame, text="製品名:").grid(row=2, column=0)
product_var = tk.StringVar()
tk.Entry(frame, textvariable=product_var, width=15).grid(row=2, column=1)

tk.Label(frame, text="シリアルNo:").grid(row=3, column=0)
serial_var = tk.StringVar()
tk.Entry(frame, textvariable=serial_var, width=15).grid(row=3, column=1)

tk.Label(frame, text="コメント:").grid(row=4, column=0)
comment_var = tk.StringVar()
tk.Entry(frame, textvariable=comment_var, width=15).grid(row=4, column=1)

tk.Label(frame, text="保存フォルダ:").grid(row=5, column=0)
tk.Button(frame, text="参照", command=select_save_dir).grid(row=5, column=1)
dir_label = tk.Label(frame, text="未選択", anchor="w", width=40)
dir_label.grid(row=5, column=2)

tk.Label(frame, text="保存形式:").grid(row=6, column=0)
format_var = tk.StringVar(value="csv")
tk.Radiobutton(frame, text="CSV", variable=format_var, value="csv").grid(row=6, column=1)
tk.Radiobutton(frame, text="JSON", variable=format_var, value="json").grid(row=6, column=2)
tk.Radiobutton(frame, text="TXT", variable=format_var, value="txt").grid(row=6, column=3)

tk.Button(frame, text="Start", command=start_logging).grid(row=7, column=0, pady=10)
tk.Button(frame, text="Stop", command=stop_logging).grid(row=7, column=1)

status_label = tk.Label(root, text="準備完了", fg="blue")
status_label.pack()

log_output = tk.Text(root, height=15, width=70)
log_output.pack(padx=10, pady=10)

refresh_ports()
root.mainloop()

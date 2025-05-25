import tkinter as tk
from tkinter import ttk
from logger.serial_reader import open_serial_port, read_serial_data
from logger.file_writer import get_log_file_path, write_log
import serial.tools.list_ports

ser = None
log_file_path = None
is_logging = False

def get_serial_ports():
    ports = serial.tools.list_ports.comports()
    return [p.device for p in ports]

def refresh_ports():
    ports = get_serial_ports()
    port_combo["values"] = ports
    port_var.set(ports[0] if ports else "なし")

def start_logging():
    global ser, is_logging, log_file_path
    port = port_var.get()
    baud = baud_var.get()

    try:
        baud = int(baud)
    except ValueError:
        log_output.insert(tk.END, "ボーレートが不正です\n")
        return

    ser = open_serial_port(port, baud)
    if ser:
        log_file_path = get_log_file_path()
        is_logging = True
        log_output.insert(tk.END, f"開始: {port} @ {baud}bps\n")
        root.after(100, read_loop)  # 100msごとに読み取り
    else:
        log_output.insert(tk.END, "ポートオープンに失敗しました\n")

def stop_logging():
    global is_logging
    is_logging = False
    if ser and ser.is_open:
        ser.close()
        log_output.insert(tk.END, "停止\n")

def read_loop():
    if is_logging and ser:
        data = read_serial_data(ser)
        if data:
            log_output.insert(tk.END, data + "\n")
            write_log(log_file_path, data)
            log_output.see(tk.END)
        root.after(100, read_loop)

# --- GUI ---
root = tk.Tk()
root.title("Serial Logger")

frame = tk.Frame(root)
frame.pack(padx=10, pady=10)

tk.Label(frame, text="COMポート:").grid(row=0, column=0)
port_var = tk.StringVar()
port_combo = ttk.Combobox(frame, textvariable=port_var, width=10)
port_combo.grid(row=0, column=1)
tk.Button(frame, text="再スキャン", command=refresh_ports).grid(row=0, column=2)
refresh_ports()

tk.Label(frame, text="ボーレート:").grid(row=1, column=0)
baud_var = tk.StringVar(value="9600")
tk.Entry(frame, textvariable=baud_var, width=10).grid(row=1, column=1)

tk.Button(frame, text="Start", command=start_logging).grid(row=2, column=0, pady=10)
tk.Button(frame, text="Stop", command=stop_logging).grid(row=2, column=1)

log_output = tk.Text(root, height=15, width=60)
log_output.pack(padx=10, pady=10)

root.mainloop()

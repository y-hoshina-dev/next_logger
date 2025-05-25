# app.py
import tkinter as tk
from logger.serial_reader import open_serial_port, read_serial_data
from logger.file_writer import write_log

def start_logging():
    # 簡略化：本来はconfig.iniから読み込んでもよい
    global ser
    ser = open_serial_port("COM3", 9600)
    log_output.insert(tk.END, "Logging started...\n")

def stop_logging():
    if ser:
        ser.close()
    log_output.insert(tk.END, "Logging stopped.\n")

app = tk.Tk()
app.title("Serial Logger GUI")

frame = tk.Frame(app)
frame.pack()

start_btn = tk.Button(frame, text="Start", command=start_logging)
stop_btn = tk.Button(frame, text="Stop", command=stop_logging)
start_btn.pack(side=tk.LEFT, padx=5)
stop_btn.pack(side=tk.LEFT, padx=5)

log_output = tk.Text(app, height=10, width=50)
log_output.pack()

app.mainloop()

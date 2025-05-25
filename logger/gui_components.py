import tkinter as tk
from tkinter import ttk, filedialog
import serial.tools.list_ports  # ← 追加

def create_gui(root, start_callback, stop_callback, pause_callback, resume_callback):
    port_var = tk.StringVar()
    baud_var = tk.StringVar(value="9600")
    format_var = tk.StringVar(value="txt")
    product_var = tk.StringVar()
    serial_var = tk.StringVar()
    comment_var = tk.StringVar()
    date_var = tk.StringVar()
    save_dir_var = tk.StringVar()

    frame = ttk.Frame(root, padding=10)
    frame.pack(fill=tk.BOTH, expand=True)

    # 利用可能なCOMポートを自動取得（なければ"未検出"）
    ports = [port.device for port in serial.tools.list_ports.comports()]
    if not ports:
        ports = ["未検出"]

    ttk.Label(frame, text="COMポート:").grid(row=0, column=0)
    port_combo = ttk.Combobox(frame, textvariable=port_var, values=ports)
    port_combo.grid(row=0, column=1)
    if ports[0] != "未検出":
        port_var.set(ports[0])  # 最初のポートを初期値に

    ttk.Label(frame, text="ボーレート:").grid(row=1, column=0)
    ttk.Entry(frame, textvariable=baud_var).grid(row=1, column=1)

    ttk.Label(frame, text="フォーマット:").grid(row=2, column=0)
    ttk.Combobox(frame, textvariable=format_var, values=["txt", "csv", "json"]).grid(row=2, column=1)

    ttk.Label(frame, text="製品名:").grid(row=3, column=0)
    ttk.Entry(frame, textvariable=product_var).grid(row=3, column=1)

    ttk.Label(frame, text="シリアル番号:").grid(row=4, column=0)
    ttk.Entry(frame, textvariable=serial_var).grid(row=4, column=1)

    ttk.Label(frame, text="コメント:").grid(row=5, column=0)
    ttk.Entry(frame, textvariable=comment_var).grid(row=5, column=1)

    ttk.Label(frame, text="日付 (例: 20250524):").grid(row=6, column=0)
    ttk.Entry(frame, textvariable=date_var).grid(row=6, column=1)

    def choose_folder():
        folder = filedialog.askdirectory()
        if folder:
            save_dir_var.set(folder)

    ttk.Button(frame, text="保存先選択", command=choose_folder).grid(row=7, column=0)
    ttk.Entry(frame, textvariable=save_dir_var).grid(row=7, column=1)

    status_label = ttk.Label(frame, text="ステータス: 未接続")
    status_label.grid(row=8, column=0, columnspan=2)

    log_output = tk.Text(frame, height=10)
    log_output.grid(row=9, column=0, columnspan=2, pady=5)

    def on_start():
        info = {
            "product": product_var.get(),
            "serial": serial_var.get(),
            "comment": comment_var.get(),
            "date": date_var.get(),
            "save_dir": save_dir_var.get()
        }
        start_callback(port_var, baud_var, format_var, info, status_label, log_output)

    ttk.Button(frame, text="開始", command=on_start).grid(row=10, column=0)
    ttk.Button(frame, text="停止", command=lambda: stop_callback(status_label)).grid(row=10, column=1)
    ttk.Button(frame, text="一時停止", command=lambda: pause_callback(status_label)).grid(row=11, column=0)
    ttk.Button(frame, text="再開", command=lambda: resume_callback(status_label)).grid(row=11, column=1)

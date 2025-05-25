# logger/serial_reader.py
import serial

def open_serial_port(port, baudrate):
    try:
        ser = serial.Serial(port, baudrate, timeout=1)
        return ser
    except serial.SerialException as e:
        print(f"Error opening port: {e}")
        return None

def read_serial_data(ser):
    if ser and ser.in_waiting:
        return ser.readline().decode("utf-8").strip()
    return None

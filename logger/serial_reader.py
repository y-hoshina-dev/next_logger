import serial

def open_serial_port(port, baudrate):
    try:
        return serial.Serial(port, baudrate, timeout=1)
    except serial.SerialException as e:
        print(f"Serial Error: {e}")
        return None

def read_serial_data(ser):
    if ser.in_waiting:
        try:
            return ser.readline().decode("utf-8").strip()
        except Exception as e:
            print(f"Read error: {e}")
    return None

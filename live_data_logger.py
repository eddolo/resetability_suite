# live_data_logger.py (Version 2 - Importable)
import serial
import time
import argparse
from pathlib import Path

# --- Configuration ---
DEFAULT_OUTPUT_FILE = Path("data/telemetry.csv")
DEFAULT_BAUD_RATE = 115200
HEADER = "timestamp,qw,qx,qy,qz\n"

def get_serial_ports():
    """Lists available serial ports on the system."""
    import serial.tools.list_ports
    ports = serial.tools.list_ports.comports()
    return [port.device for port in ports]

def start_logging(port: str, baud_rate: int, output_file: Path):
    """
    Connects to a serial port, reads quaternion data, and logs it to a CSV file.
    This is the core function that can be called from other scripts.
    """
    print(f"Attempting to connect to port '{port}' at {baud_rate} baud...")
    
    try:
        with serial.Serial(port, baud_rate, timeout=2) as ser, open(output_file, 'w', newline='') as f:
            print(f"✅ Connection successful! Logging data to '{output_file}'.")
            
            f.write(HEADER)
            f.flush()
            start_time = time.time()
            
            while True:
                line = ser.readline()
                if not line:
                    continue
                try:
                    data_str = line.decode('utf-8').strip()
                    values = [float(v) for v in data_str.split(',')]
                    
                    if len(values) == 4:
                        qw, qx, qy, qz = values
                        timestamp = time.time() - start_time
                        log_line = f"{timestamp:.4f},{qw:.6f},{qx:.6f},{qy:.6f},{qz:.6f}\n"
                        f.write(log_line)
                        f.flush()
                except (UnicodeDecodeError, ValueError):
                    # In a background process, we might not want to print every error
                    pass # Silently ignore malformed lines
                    
    except serial.SerialException as e:
        print(f"❌ LOGGING PROCESS ERROR: Could not open serial port '{port}'. Reason: {e}")
    except Exception as e:
        print(f"\nLOGGING PROCESS ERROR: An unexpected error occurred: {e}")
    finally:
        print("LOGGING PROCESS STOPPED.")

def main():
    """This function handles the command-line interface part."""
    parser = argparse.ArgumentParser(description="Live Data Logger for the SO(3) Resetability Suite")
    
    parser.add_argument('-p', '--port', type=str, help="The serial port to connect to.")
    parser.add_argument('-b', '--baud', type=int, default=DEFAULT_BAUD_RATE, help=f"Baud rate (default: {DEFAULT_BAUD_RATE}).")
    parser.add_argument('-o', '--output', type=Path, default=DEFAULT_OUTPUT_FILE, help=f"Output CSV file (default: {DEFAULT_OUTPUT_FILE}).")
    parser.add_argument('--list-ports', action='store_true', help="List available serial ports and exit.")
    
    args = parser.parse_args()
    
    if args.list_ports:
        print("Available serial ports:")
        ports = get_serial_ports()
        if ports:
            for p in ports: print(f"  - {p}")
        else:
            print("  No serial ports found.")
    elif args.port:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        # We add a try/except here for the KeyboardInterrupt for command-line use
        try:
            start_logging(args.port, args.baud, args.output)
        except KeyboardInterrupt:
            print("\n🛑 Logging stopped by user.")
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
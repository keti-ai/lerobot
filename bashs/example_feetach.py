import serial
import time

# Serial port settings (update based on your setup)
SERIAL_PORT = "/dev/ttyACM0"  # Change this based on your system
BAUD_RATE = 1000000

# Open serial connection
ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)

def send_command(command):
    """Send a command to the servo and print the response."""
    ser.write(bytes(command))
    time.sleep(0.1)
    response = ser.read(ser.in_waiting)
    print(f"Response: {response.hex().upper()}")

def calculate_checksum(data):
    """Calculate checksum based on protocol."""
    return (~sum(data) & 0xFF)

def set_servo_id(old_id, new_id):
    """Set a new ID for the servo."""
    command = [0xFF, 0xFF, old_id, 0x04, 0x03, 0x05, new_id]
    command.append(calculate_checksum(command[2:]))  # Append checksum
    send_command(command)

def move_servo(servo_id, position, speed):
    """Move the servo to a specified position and speed."""
    pos_low, pos_high = position & 0xFF, (position >> 8) & 0xFF
    speed_low, speed_high = speed & 0xFF, (speed >> 8) & 0xFF
    command = [0xFF, 0xFF, servo_id, 0x09, 0x03, 0x2A, pos_low, pos_high, 0x00, speed_low, speed_high]
    command.append(calculate_checksum(command[2:]))  # Append checksum
    send_command(command)

# Example usage
if __name__ == "__main__":
    time.sleep(2)  # Wait for serial connection

    # Set servo ID (if needed)
    # set_servo_id(0xFE, 0x01)  # Change broadcast ID to 1

    # Move servo ID 1 to position 2048 at speed 1000
    move_servo(0x06, 2048, 1000)

    ser.close()

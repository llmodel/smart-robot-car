import socket
import sys
import time
from pynput import keyboard # Import the keyboard listener

# --- Connection Setup (Same as before) ---
ip = "192.168.4.1"
port = 100
print(f'Connecting to {ip}:{port}...')
car_socket = None
try:
    car_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    car_socket.settimeout(10.0)
    car_socket.connect((ip, port))
    car_socket.settimeout(2.0) # Read timeout
    print('Connected!')
except socket.timeout:
    print(f'Error: Connection to {ip}:{port} timed out.')
    sys.exit()
except socket.error as e:
    print(f'Error connecting: {e}')
    sys.exit()
except Exception as e:
    print(f'Error during setup: {e}')
    if car_socket: car_socket.close()
    sys.exit()


# --- Define the Key-to-Command Mapping ---
# Use lowercase keys for easier lookup
# Adjust speeds (D2 value) as desired
key_command_map = {
    # --- Movement ---
    'w': '{ "N": 102 , "D1":1 , "D2": 100 }',  # Forward (Speed 100)
    's': '{ "N": 102 , "D1":2 , "D2": 100 }',  # Backward (Speed 100)
    'a': '{ "N": 102 , "D1":3 , "D2": 150 }',  # Left (Turn Speed 150)
    'd': '{ "N": 102 , "D1":4 , "D2": 150 }',  # Right (Turn Speed 150)
    'q': '{ "N": 102 , "D1":5 , "D2": 180 }',  # Forward Left (Example)
    'e': '{ "N": 102 , "D1":6 , "D2": 180 }',  # Forward Right (Example)
    'z': '{ "N": 102 , "D1":7 , "D2": 180 }',  # Backward Left (Example)
    'c': '{ "N": 102 , "D1":8 , "D2": 180 }',  # Backward Right (Example)

    # --- Stop ---
    'x': '{ "N": 102 , "D1":0 , "D2": 0 }',    # Stop all motor movement

    # --- Other Actions (Add examples based on robot capabilities) ---
    # 'h':  '{ "N": 103, "Action": "Honk" }',  # Hypothetical Honk
    # 'l':  '{ "N": 104, "State": 1 }',       # Hypothetical Lights ON
    # 'k':  '{ "N": 104, "State": 0 }',       # Hypothetical Lights OFF
    # Add more keys and commands here
}


# --- Function to Send Commands/Messages (Same as before) ---
def send_message(message_str):
    """Encodes and sends a string message to the car socket."""
    if not car_socket:
        print("Error: Socket is not connected.")
        return
    try:
        print(f"Sending Command: {message_str}")
        car_socket.sendall(message_str.encode())
    except socket.error as e:
        print(f"Error sending message '{message_str}': {e}")
    except Exception as e:
        print(f"Unexpected error in send_message: {e}")


# --- Keyboard Press Event Handler (Modified to use the map) ---
def on_press(key):
    """Callback function executed when a key is pressed."""
    global running
    command_to_send = None # Initialize command to None

    try:
        # Get the character representation and convert to lowercase
        char = key.char.lower()

        # Look up the character in the command map
        if char in key_command_map:
            command_to_send = key_command_map[char]
            print(f"\nKey '{char}' pressed - Sending: {command_to_send}")

        # else: # Optional: Handle keys not in the map
            # print(f"\nKey '{char}' pressed - No command mapped.")

    except AttributeError:
        # Handle special keys if needed (e.g., map Spacebar to Stop)
        # Note: Add 'space': '{...}' entry to key_command_map if you use this
        # if key == keyboard.Key.space:
        #     char_name = 'space'
        #     if char_name in key_command_map:
        #         command_to_send = key_command_map[char_name]
        #         print(f"\nKey '{char_name}' pressed - Sending: {command_to_send}")
        # elif key == keyboard.Key.esc: # Example: Stop program on Esc
        #      print("\nEscape key pressed - Stopping program!")
        #      running = False
        pass # Ignore other special keys for now

    except Exception as e:
         print(f"\nError in on_press callback: {e}")

    # Send the command if one was found for the pressed key
    if command_to_send:
        try:
            send_message(command_to_send)
        except Exception as send_err:
             print(f"Error sending command after key press: {send_err}")
             # Decide if a send failure should stop the program, etc.


# --- Start Keyboard Listener (Same as before) ---
print("Starting keyboard listener...")
listener = keyboard.Listener(on_press=on_press)
listener.start()

# -----------------------------------------------
# ---  Main Loop for Receiving and Heartbeat  ---
# -----------------------------------------------
receive_buffer = ""
running = True

print("\n-----------------------------------------")
print("Main network loop started.")
print("Mapped keys: ", list(key_command_map.keys())) # Show mapped keys
print("Press mapped keys to send commands.")
print("Press Ctrl+C to stop the program.")
print("-----------------------------------------\n")

try:
    while running:
        try:
            chunk = car_socket.recv(1024)
            if not chunk:
                print("\nConnection closed by the server.")
                running = False; break

            receive_buffer += chunk.decode()
            while '{' in receive_buffer and '}' in receive_buffer:
                start_index = receive_buffer.find('{')
                end_index = receive_buffer.find('}', start_index)
                if end_index == -1: break

                message = receive_buffer[start_index : end_index + 1]
                receive_buffer = receive_buffer[end_index + 1 :]
                print(f"Received: {message}")

                if message == "{Heartbeat}":
                    # print("Heartbeat received. Sending reply...") # Make less verbose
                    try: send_message("{Heartbeat}")
                    except Exception as send_err:
                        print(f"Failed to send heartbeat reply: {send_err}"); running = False; break
                # else: (Handle other specific incoming messages if needed)

        except socket.timeout: continue # Normal, allows loop check
        except (socket.error, ConnectionAbortedError) as e: print(f"\nSocket error: {e}"); running = False
        except UnicodeDecodeError as e: print(f"\nDecode error: {e}"); receive_buffer = ""
        except Exception as e: print(f"\nLoop error: {e}"); running = False

except KeyboardInterrupt: print("\nCtrl+C detected. Stopping..."); running = False
finally:
    print("\nPerforming cleanup...")
    if 'listener' in locals() and listener.is_alive(): print("Stopping keyboard listener..."); listener.stop()
    if car_socket: print("Closing socket."); car_socket.close() # Optional final stop command removed for brevity
    print("Program terminated.")
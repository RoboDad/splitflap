#!/usr/bin/env python3
"""
Quick-and-dirty demo controller for splitflap display
Sends canned messages via USB serial for show demos

Commands:
    1-9: Send specific demo message
    a: Auto-cycle through all messages
    r: Recalibrate all modules
    q: Quit
"""

import serial
import serial.tools.list_ports
import time
import sys
import msvcrt  # For Windows keyboard input

# Configuration
BAUD_RATE = 230400
NUM_MODULES = 24  # Adjust to your display size

# Demo messages - customize these for your show!
# Special characters (color blocks):
#   g = green block    r = red block      y = yellow block
#   p = purple block   w = white block
# Use UPPERCASE for letters, lowercase for color blocks
DEMO_MESSAGES = [
    "gpgpgpgpgpgpgpgpgpgpgpgp",
    "    WELCOME!  TO THE    ",
    " SAN DIEGUITO ART GUILD ",
    "      ART, GARDEN       ",
    "  AND STUDIO TOUR 2026! ",
    "  MOTHER'S DAY WEEKEND  ",
    "   THIS IS A SPLITFLAP  ",
    "DISPLAY... THROWBACK TO ",
    "      A BYGONE ERA!     ",
]

def find_splitflap_port():
    """Find the splitflap USB serial port"""
    print("Looking for splitflap device...")
    ports = serial.tools.list_ports.comports()
    
    # ESP32 typically shows as Silicon Labs CP210x or similar
    for port in ports:
        print(f"  Found: {port.device} - {port.description}")
        # You can add specific filtering here if needed
        if "CP210" in port.description or "USB" in port.description:
            return port.device
    
    # If no automatic match, show all ports and ask user
    if ports:
        print("\nEnter COM port manually (e.g., COM3):")
        return input("> ").strip()
    
    print("No serial ports found!")
    return None

def send_text(ser, text):
    """Send text command to splitflap display"""
    # Pad or trim to display width (preserve case for color blocks!)
    text = text[:NUM_MODULES].ljust(NUM_MODULES)
    command = f"={text}\n".encode('ascii')
    
    print(f"Sending: {text}")
    ser.write(command)
    ser.flush()
    
    # Wait a bit for the display to update
    # Adjust timing based on your needs
    time.sleep(0.1)

def recalibrate(ser):
    """Recalibrate all modules"""
    print("Recalibrating all modules...")
    ser.write(b'@')
    ser.flush()

def auto_cycle(ser, delay=7):
    """Auto-cycle through all demo messages"""
    print(f"\nAuto-cycling (press any key to stop)...")
    print(f"Display time: {delay} seconds per message\n")
    
    try:
        while True:
            for i, msg in enumerate(DEMO_MESSAGES, 1):
                print(f"[{i}/{len(DEMO_MESSAGES)}] ", end='')
                send_text(ser, msg)
                
                # Wait with ability to interrupt
                start = time.time()
                while time.time() - start < delay:
                    if msvcrt.kbhit():
                        msvcrt.getch()  # Clear the key
                        print("\nAuto-cycle stopped.")
                        return
                    time.sleep(0.1)
    except KeyboardInterrupt:
        print("\nAuto-cycle stopped.")

def print_menu():
    """Print the command menu"""
    print("\n" + "="*50)
    print("SPLITFLAP DEMO CONTROLLER")
    print("="*50)
    print("\nDemo Messages:")
    for i, msg in enumerate(DEMO_MESSAGES, 1):
        print(f"  {i}: {msg}")
    print("\nCommands:")
    print("  a: Auto-cycle through all messages")
    print("  r: Recalibrate all modules")
    print("  q: Quit")
    print("\nPress a key (1-9, a, r, q)...")

def main():
    # Find and open serial port
    port = find_splitflap_port()
    if not port:
        print("Could not find splitflap device!")
        input("Press Enter to exit...")
        return
    
    print(f"\nConnecting to {port} at {BAUD_RATE} baud...")
    
    try:
        ser = serial.Serial(port, BAUD_RATE, timeout=1)
        time.sleep(2)  # Wait for connection to stabilize
        print("Connected!")
        
        # Send initial message
        send_text(ser, DEMO_MESSAGES[0])
        
        while True:
            print_menu()
            
            # Wait for keypress (Windows)
            key = msvcrt.getch().decode('ascii').lower()
            
            if key == 'q':
                print("\nExiting...")
                break
            elif key == 'r':
                recalibrate(ser)
            elif key == 'a':
                auto_cycle(ser)
            elif key in '123456789':
                idx = int(key) - 1
                if idx < len(DEMO_MESSAGES):
                    send_text(ser, DEMO_MESSAGES[idx])
                else:
                    print(f"No message #{key}")
            else:
                print(f"Unknown command: {key}")
        
        ser.close()
        
    except serial.SerialException as e:
        print(f"\nSerial error: {e}")
        input("Press Enter to exit...")
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    
    print("Goodbye!")

if __name__ == '__main__':
    main()

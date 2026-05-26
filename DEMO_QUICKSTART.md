# Quick Demo Setup Guide

## Installation (5 minutes)

1. **Install Python dependency:**
   ```powershell
   pip install pyserial
   ```

2. **Connect your splitflap display via USB**

3. **Customize demo messages** (optional):
   Edit `demo_controller.py` and change the `DEMO_MESSAGES` list

4. **Run the demo:**
   ```powershell
   python demo_controller.py
   ```

## Usage at the Show

### Manual Control
- Press **1-9** to show specific messages
- Press **a** for auto-cycle mode (5 seconds per message)
- Press **r** to recalibrate if needed
- Press **q** to quit

### Auto-Cycle Mode
Perfect for when you're talking to visitors - just press **'a'** and let it run.
Press any key to stop and return to manual control.

## Customizing Messages

Edit these lines in `demo_controller.py`:

```python
DEMO_MESSAGES = [
    "YOUR MESSAGE 1",
    "YOUR MESSAGE 2",
    # ... up to 9 messages
]
```

Tips:
- Messages are auto-padded/trimmed to your display width (24 modules)
- Use UPPERCASE for best readability
- Stick to: A-Z, 0-9, space, period, comma, apostrophe

## Troubleshooting

**"No serial ports found"**
- Make sure the display is plugged in via USB
- Check Device Manager for COM port
- May need CH340/CP210x drivers

**Wrong baud rate error**
- Script uses 230400 (chainlink default)
- If you have a different board, edit `BAUD_RATE` in the script

**Display not responding**
- Press 'r' to recalibrate
- Check that firmware is uploaded correctly
- Try unplugging and reconnecting USB

## Fallback Plan

If something goes wrong at the show, you can flash a hardcoded demo into firmware:
1. Flash firmware before leaving
2. Take a USB cable just in case
3. Have PlatformIO ready on laptop

But the serial controller should be rock solid! ✨

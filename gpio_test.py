import pigpio
import time

pi = pigpio.pi()

BUTTON_PINS = [17, 16, 26]  # Adjust these to match your config

def callback(gpio, level, tick):
    print(f"Button press detected on GPIO {gpio}, level: {level}")

for pin in BUTTON_PINS:
    pi.set_mode(pin, pigpio.INPUT)
    pi.set_pull_up_down(pin, pigpio.PUD_UP)
    pi.callback(pin, pigpio.EITHER_EDGE, callback)

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    pi.stop()
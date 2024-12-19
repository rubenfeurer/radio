import pigpio
import time
import subprocess
from config.config import settings

pi = pigpio.pi()

BUTTON_PINS = [
    settings.BUTTON_PIN_1,
    settings.BUTTON_PIN_2,
    settings.BUTTON_PIN_3
]

def callback(gpio, level, tick):
    if gpio == settings.ROTARY_SW and level == 0:  # Button pressed
        print(f"Button press detected on rotary switch (GPIO {gpio})")
    else:
        print(f"Button press detected on GPIO {gpio}, level: {level}")

# Setup pins
for pin in BUTTON_PINS:
    pi.set_mode(pin, pigpio.INPUT)
    pi.set_pull_up_down(pin, pigpio.PUD_UP)
    pi.callback(pin, pigpio.EITHER_EDGE, callback)

# Setup rotary switch
pi.set_mode(settings.ROTARY_SW, pigpio.INPUT)
pi.set_pull_up_down(settings.ROTARY_SW, pigpio.PUD_UP)
pi.callback(settings.ROTARY_SW, pigpio.EITHER_EDGE, callback)

try:
    print("Monitoring GPIO pins. Double-click rotary switch to reboot.")
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    pi.stop()
import pigpio

pi = pigpio.pi()
if not pi.connected:
    print("Failed to connect to pigpio daemon")
else:
    print("Connected to pigpio daemon")
    pi.set_mode(17, pigpio.INPUT)
    pi.set_pull_up_down(17, pigpio.PUD_UP)
    print("GPIO setup successful")
    pi.stop()

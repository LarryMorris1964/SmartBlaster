# Minimal camera test script for Raspberry Pi using picamera2
from picamera2 import Picamera2
import time

picam = Picamera2()
picam.start()
time.sleep(2)  # Allow camera to warm up
picam.capture_file("test.jpg")
picam.close()
print("Image captured as test.jpg")

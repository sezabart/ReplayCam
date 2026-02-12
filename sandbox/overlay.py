import time
import cv2
import numpy as np
from picamera2 import Picamera2, MappedArray

# --- CONFIG ---
RESOLUTION = (1920, 1080)
OVERLAY_FILE = "overlay.png"
OUTPUT_FILE = "overlay.jpg"

class OverlayTester:
    def __init__(self):
        print("[TEST] Initializing Camera...")
        self.picam2 = Picamera2(0)
        
        # Load overlay once
        self.overlay = cv2.imread(OVERLAY_FILE, cv2.IMREAD_UNCHANGED)
        if self.overlay is None:
            raise FileNotFoundError(f"Could not find {OVERLAY_FILE}")

    def apply_overlay(self, request):
        """
        This is called by Picamera2 immediately after the frame is captured 
        but before it is saved/processed.
        """
        with MappedArray(request, "main") as m:
            # Picamera2 YUV420 stores Y (luminance) in the first plane.
            # We apply the overlay to the Y plane for a quick greyscale check,
            # OR convert the whole buffer. For testing overlays, we'll 
            # treat the MappedArray as a buffer we can manipulate.
            
            # Simple proof-of-concept: Draw a white box in the Y channel
            # Y plane is the first (width * height) bytes
            Y = m[0:RESOLUTION[0]*RESOLUTION[1]].reshape((RESOLUTION[1], RESOLUTION[0]))
            
            # Draw a literal box to prove callback is hitting
            cv2.rectangle(Y, (50, 50), (500, 500), (255), -1)
            
            # Note: For a full color PNG overlay on YUV, you'd usually convert 
            # the PNG to YUV and blend planes, but this confirms the callback works.
            print("[CALLBACK] Overlay logic executed on frame.")

    def run_test(self):
        # Configure for YUV420
        config = self.picam2.create_still_configuration(main={"size": RESOLUTION, "format": "YUV420"})
        self.picam2.configure(config)
        
        # Set the callback
        self.picam2.pre_callback = self.apply_overlay
        
        self.picam2.start()
        print(f"[TEST] Capturing single frame to {OUTPUT_FILE}...")
        
        # Capturing as JPEG so you can actually open it on your PC to see results
        self.picam2.capture_file(OUTPUT_FILE)
        
        self.picam2.stop()
        print("[TEST] Done.")

if __name__ == "__main__":
    tester = OverlayTester()
    tester.run_test()
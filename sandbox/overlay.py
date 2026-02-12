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
        self.overlay =cv2.rotate(cv2.imread(OVERLAY_FILE, cv2.IMREAD_GRAYSCALE), cv2.ROTATE_90_CLOCKWISE)
        _, self.overlay_mask = cv2.threshold(self.overlay, 1, 255, cv2.THRESH_BINARY)
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

            print(f"{m.array.shape=}")

            # Draw a rectangle to prove its being hit
            #cv2.rectangle(m.array, (50, 50), (50, 50), (255), -1)

            # 1. Grab JUST the visual part of the buffer (1920x1080)
            # This is a 'view', not a copy, so it's lightning fast.
            y_plane = m.array[0:1080, 0:1920]
            print(f"{y_plane.shape=}")

            # 2. Create the blank mask at the correct visual size
            blank = np.zeros((1080, 1920), dtype=np.uint8)
            
            # 3. Draw your rectangle
            cv2.rectangle(blank, (250, 250), (50, 50), 255, -1)

            # 4. Stamp it onto the Y-plane
            #cv2.copyTo(src=blank, mask=blank, dst=y_plane)

            # 5. Stamp the prepared bitmap from overlay onto it
            print(f"{self.overlay.shape=}")
            cv2.copyTo(src=self.overlay, mask=self.overlay_mask, dst=y_plane)

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
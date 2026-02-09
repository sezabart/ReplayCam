import time
import os
import datetime
import subprocess
import signal
import sys
import time

from gpiozero import Button
from picamera2 import Picamera2, MappedArray
from picamera2.encoders import H264Encoder
from picamera2.outputs import CircularOutput

import cv2

# --- REPLAYCAM CONFIG ---
# Location of stored clips
STORAGE_PATH = "recordings"
# Overlay now via bitmap on picamera2
OVERLAY = "overlay.png"
# GPIO pin of button (or remote)
BUTTON_PIN = 17 
# Seconds before trigger to record (action)
PRE_TRIGGER_DURATION = 25
# Seconds after trigger to record (celebration)
POST_TRIGGER_DURATION = 5
# Video settings
RESOLUTION = (1920, 1080)
FPS = 25
BITRATE = 15000000 # 15Mbps bitrate

# Buffer size
BUFFER_FRAMES = PRE_TRIGGER_DURATION * FPS 

# Ensure folder exists
os.makedirs(STORAGE_PATH, exist_ok=True)

class ReplaySystem:
    def __init__(self):
        print("[REPLAYCAM] Initializing system")
        self.picam2 = Picamera2(0) # Camera 0
        self.encoder = None
        self.output = None
        self.is_running = False

    def apply_overlay(self, request):
        with MappedArray(request, "main") as m:
            cv2.add(m.array, self.overlay)

    def start(self):
        # Configure Camera
        config = self.picam2.create_video_configuration(
            main={"size": RESOLUTION, "format": "YUV420"}, 
            controls={"FrameDurationLimits": (int(1000000 / FPS), int(1000000 / FPS))}
        )
        self.picam2.configure(config)
        

        # Overlay
        self.overlay = cv2.imread(OVERLAY, cv2.IMREAD_UNCHANGED) # OpenCV will read png into simple bitmap with alpha channel
        if self.overlay.shape[:2] == RESOLUTION:
            self.picam2.pre_callback = self.apply_overlay
        else:
            print(f"[ERROR] Overlay is wrong dimensions: {self.overlay.shape[:2]}")

        self.picam2.start()

        # Overlay
        self.overlay = cv2.imread(OVERLAY, cv2.IMREAD_UNCHANGED) # OpenCV will read png into simple bitmap with alpha channel
        if self.overlay.shape[:2] == RESOLUTION:
            self.picam2.pre_callback = self.apply_overlay
        else:
            print(f"[ERROR] Overlay is wrong dimensions: {self.overlay.shape[:2]}")

        self.picam2.start()

        # Encoder & Buffer Setup
        self.encoder = H264Encoder(bitrate=BITRATE, repeat=True)  #H264 is best supported everywhere
        self.output = CircularOutput(buffersize=BUFFER_FRAMES) # Will keep recording in RAM looping over itself untill stopped
        
        # Start opname naar RAM
        self.picam2.start_recording(self.encoder, self.output)
        self.is_running = True
        print("[KLUTCH] Systeem ONLINE. Buffer loopt in RAM.")

    def apply_overlay(request):
        with MappedArray(request, "main") as m:
            cv2.add(m.array, self.overlay)

    def trigger_action(self):
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        raw_filename = os.path.join(STORAGE_PATH, f"raw_{timestamp}.h264")
        final_filename = os.path.join(STORAGE_PATH, f"replay_{timestamp}.mp4")
        
        print(f"\n[ACTION] Triggered! Dumping buffer to: {raw_filename}")
        
        # Start pushing buffer to disk and add the post trigger
        self.output.fileoutput = raw_filename
        self.output.start()
        print(f"[WRITING] {PRE_TRIGGER_DURATION}s writing to file, now recording {POST_TRIGGER_DURATION}s extra.")
        time.sleep(POST_TRIGGER_DURATION) 
        self.output.stop()
        
        # FUTURE: Sound recording should be stopped here too.

        print("[PROCESSING] Packaging into MP4 container")
        self.process_video(raw_filename, final_filename)

    def process_video(self, input_file, output_file):
        # Transpose=1 rotates 90 degrees, 2 for 270 (the other way)
        # [0:v] is the raw video input.
        filters = "[0:v]transpose=2[rotated]" 
        
        final_map = "[rotated]" # Make the standard output the rotated one

        if self.has_overlay:
            # If overlay, add it on top op video
            # ASSUMING OVERLAY IS SAME AS RESOLUTION
            filters += ";[rotated][1:v]overlay=0:0[output]"
            final_map = "[output]"

        cmd = [
            'ffmpeg', '-y',
            '-r', str(FPS),          # Set framerate before input for raw streams
            '-i', input_file,
            '-c:v', 'copy',          # Direct stream copy (No re-encoding!)
            '-metadata:s:v:0', 'rotate=90', # Metadata rotation (Fast & low RAM)
            '-movflags', '+faststart',     # Better for mobile playback
            output_file
        ])
        
        try:
            start_time = time.time()
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print(f"[SUCCESS] Output to: {output_file}, took {time.time()-start_time} seconds.")
            os.remove(input_file)
            
        except subprocess.CalledProcessError as e:
            print(f"[ERROR] While processing raw video: {e}")

    def stop(self):
        if self.is_running:
            print("\n[REPLAYCAM] Shutting down...")
            self.picam2.stop_recording()
            self.picam2.stop()
            self.is_running = False

# --- MAIN LOOP ---

def main():
    system = ReplaySystem()
    button = Button(BUTTON_PIN, pull_up=False)

    def signal_handler(sig, frame):
        system.stop()
        sys.exit(0)

    # Deals with ctrl+C nicely
    signal.signal(signal.SIGINT, signal_handler)

    try:
        system.start()
        print("[INFO] Ready to go, initiate trigger to record a clip.")

        while True:
            button.wait_for_press()
            
            system.trigger_action()
            
            print("[INFO] Ready for next round...\n")
            # Short cooldown
            time.sleep(1)

    except Exception as e:
        print(f"[CRITICAL ERROR] {e}")
        system.stop()

if __name__ == "__main__":
    main()
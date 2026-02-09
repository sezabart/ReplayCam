import time
import os
import datetime
import subprocess
import signal
import sys
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
# Hoeveel seconden 'terug in de tijd' (de actie)
PRE_TRIGGER_DURATION = 25
# Seconds after trigger to record (celebration)
POST_TRIGGER_DURATION = 5
# Video settings
RESOLUTION = (1920, 1080)
FPS = 25
BITRATE = 15000000 # 15Mbps bitrate

# Berekende buffer grootte
BUFFER_FRAMES = PRE_TRIGGER_DURATION * FPS 

# Zorg dat de map bestaat
os.makedirs(STORAGE_PATH, exist_ok=True)

class ReplaySystem:
    def __init__(self):
        print("[KLUTCH] Systeem initialiseren...")
        self.picam2 = Picamera2(0) # Camera 0
        self.encoder = None
        self.output = None
        self.is_running = False

    def apply_overlay(self, request):
        with MappedArray(request, "main") as m:
            cv2.add(m.array, self.overlay)

    def start(self):
        # Configureer Camera (1080p @ 30fps)
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

        # Encoder & Buffer Setup
        self.encoder = H264Encoder(bitrate=BITRATE, repeat=True)
        self.output = CircularOutput(buffersize=BUFFER_FRAMES)
        
        # Start opname naar RAM
        self.picam2.start_recording(self.encoder, self.output)
        self.is_running = True
        print("[KLUTCH] Systeem ONLINE. Buffer loopt in RAM.")

    def trigger_action(self):
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        raw_filename = os.path.join(STORAGE_PATH, f"raw_{timestamp}.h264")
        final_filename = os.path.join(STORAGE_PATH, f"replay_{timestamp}.mp4")
        
        print(f"\n[ACTION] Trigger ontvangen! Dumpen naar: {raw_filename}")
        
        # 1. Schrijf buffer (verleden) + post-roll (toekomst) naar disk
        self.output.fileoutput = raw_filename
        self.output.start()
        time.sleep(POST_TRIGGER_DURATION) 
        self.output.stop()
        
        print("[PROCESSING] Start conversie & branding...")
        self.process_video(raw_filename, final_filename)

    def process_video(self, input_file, output_file):
        # Now switched to stream copy to just put the existing h264 in a container
        # Massively faster but no support for overlay
        # Since we are using stream copy (-c:v copy), we cannot use -filter_complex.
        # We use metadata to tell the phone to play the video rotated.
        # '270' metadata is equivalent to transpose=2 (90 deg counter-clockwise).
        
        cmd = [
            'ffmpeg', '-y',
            '-r', str(FPS),          # Set framerate before input for raw streams
            '-i', input_file,
            '-c:v', 'copy',          # Direct stream copy (No re-encoding!)
            '-metadata:s:v:0', 'rotate=90', # Metadata rotation (Fast & low RAM)
            '-movflags', '+faststart',     # Better for mobile playback
            output_file
        ]
        try:
            # Run FFmpeg
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print(f"[SUCCESS] High-speed repackaging complete: {output_file}")
            
            # Cleanup
            os.remove(input_file)
            
        except subprocess.CalledProcessError as e:
            print(f"[ERROR] Fout tijdens verwerken video: {e}")

            

    def stop(self):
        if self.is_running:
            print("\n[KLUTCH] Afsluiten...")
            self.picam2.stop_recording()
            self.picam2.stop()
            self.is_running = False

# --- MAIN LOOP ---

def main():
    system = ReplaySystem()
    button = Button(BUTTON_PIN, bounce_time=0.1)

    def signal_handler(sig, frame):
        system.stop()
        sys.exit(0)

    # Vang CTRL+C netjes op
    signal.signal(signal.SIGINT, signal_handler)

    try:
        system.start()
        print("[INFO] Druk op de knop om een highlight op te slaan.")

        while True:
            button.wait_for_press()
            
            # Blokkeer nieuwe triggers tijdens verwerking (simpele 'cooldown')
            system.trigger_action()
            
            print("[INFO] Wachten op volgende rally...\n")
            # Korte extra pauze om spammen te voorkomen
            time.sleep(1)

    except Exception as e:
        print(f"[CRITICAL ERROR] {e}")
        system.stop()

if __name__ == "__main__":
    main()
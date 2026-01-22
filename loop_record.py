import time
import os
import datetime
import subprocess
import signal
import sys
from gpiozero import Button
from picamera2 import Picamera2
from picamera2.encoders import H264Encoder
from picamera2.outputs import CircularOutput

# --- KLUTCH CONFIGURATIE ---
# Opslaglocatie voor de clips
STORAGE_PATH = "recordings"
# Naam van je overlay bestand (moet 1080x1920 PNG zijn)
OVERLAY_FILE = "Overlay.png"
# GPIO pin van de drukknop
BUTTON_PIN = 17 
# Hoeveel seconden 'terug in de tijd' (de actie)
PRE_TRIGGER_DURATION = 25
# Hoeveel seconden 'na de knop' (de reactie/juichen)
POST_TRIGGER_DURATION = 2
# Video instellingen
FPS = 30
BITRATE = 15000000 # 15Mbps voor hoge kwaliteit raw input

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

        # Controleer overlay
        if not os.path.exists(OVERLAY_FILE):
            print(f"[WARNING] Overlay bestand niet gevonden op: {OVERLAY_FILE}")
            print("Video's worden verwerkt ZONDER overlay.")
            self.has_overlay = False
        else:
            self.has_overlay = True

    def start(self):
        # Configureer Camera (1080p @ 30fps)
        config = self.picam2.create_video_configuration(
            main={"size": (1920, 1080), "format": "YUV420"}, 
            controls={"FrameDurationLimits": (int(1000000 / FPS), int(1000000 / FPS))}
        )
        self.picam2.configure(config)
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
        # Stap 1: Roteer de video 90 graden met de klok mee (transpose=1)
        # Gebruik transpose=2 voor tegen de klok in als je camera andersom hangt.
        # [0:v] is de raw video input.
        filters = "[0:v]transpose=2[rotated]" 
        
        final_map = "[rotated]" # Standaard output is de gedraaide video

        if self.has_overlay:
            # Als er een overlay is, plakken we die BOVENOP de gedraaide video
            # We gaan ervan uit dat je Overlay.png nu 1080x1920 (Staand) is!
            filters += ";[rotated][1:v]overlay=0:0[output]"
            final_map = "[output]"

        cmd = [
            'ffmpeg', '-y',
            '-framerate', str(FPS),
            '-i', input_file
        ]

        if self.has_overlay:
            cmd.extend(['-i', OVERLAY_FILE])
        
        cmd.extend([
            '-filter_complex', filters,
            '-map', final_map, # Zorg dat we de juiste stream pakken
            '-c:v', 'libx264',
            '-preset', 'ultrafast',
            '-crf', '23',
            '-pix_fmt', 'yuv420p',
            output_file
        ])
        
        try:
            # Draai FFmpeg
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print(f"[SUCCESS] Verticale Clip klaar: {output_file}")
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
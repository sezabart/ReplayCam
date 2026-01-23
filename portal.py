import os
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
import urllib.parse
import mimetypes

# Instellingen
PORT = 80
RECORDINGS_DIR = "recordings"  # Zorg dat deze map bestaat
HOST_IP = "192.168.4.1"
DOMAIN_NAME = "replay.cam"   # De vriendelijke URL

class CaptiveHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        # 1. Parse de aanvraag
        parsed_path = urllib.parse.urlparse(self.path)
        path = parsed_path.path
        query = urllib.parse.parse_qs(parsed_path.query)

        # 2. Apple/Android Captive Probes
        # Dit zijn checks van telefoons om te zien of er internet is.
        # We sturen ze door naar onze pagina, of geven 'Success' als we dat zouden willen.
        captive_probes = [
            "/hotspot-detect.html", # Apple
            "/generate_204",        # Android
            "/ncsi.txt",            # Windows
            "/connecttest.txt"
        ]
        
        # 3. Video bestanden serveren
        if path.startswith("/video/"):
            self.serve_video_file(path, is_download='download' in query)
            return

        # 4. Redirect check
        # Als de gebruiker NIET op ons IP of ons domein zit (bijv. hij typt google.com),
        # stuur hem dan naar onze vriendelijke URL.
        host = self.headers.get('Host', '')
        
        # We checken of het huidige adres toegestaan is.
        # Als het een captive probe is, laten we het doorgaan (zodat de popup verschijnt).
        if HOST_IP not in host and DOMAIN_NAME not in host and path not in captive_probes:
            self.send_response(302)
            self.send_header('Location', f'http://{HOST_IP}/')
            self.end_headers()
            return

        # 5. Serveer de hoofdpagina
        print(f"{host=}")

        if self.is_ios_device() and (HOST_IP in host or path in captive_probes):
            self.serve_instruction()
        else:
            self.serve_video_list()

    def is_ios_device(self):
        user_agent = self.headers.get('User-Agent', '').lower()
        return any(device in user_agent for device in ['iphone', 'ipod', 'ipad'])


    def serve_video_list(self):
        videos = []
        if os.path.exists(RECORDINGS_DIR):
            for f in os.listdir(RECORDINGS_DIR):
                if f.lower().endswith(('.mp4', '.mov', '.mkv', '.avi')) and not f.startswith('raw'):
                    size = os.path.getsize(os.path.join(RECORDINGS_DIR, f))
                    videos.append({"name": f, "size": self.format_size(size)})

            # Sorteer op basis van naam (replay_yyyymmdd_hhmmss.mp4)
            videos.sort(key=lambda x: x["name"], reverse=True)

        # HTML in het Nederlands
        html = f"""
<!DOCTYPE html>
<html lang="nl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Replay Video's</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; background: #f2f2f7; margin: 0; padding: 15px; }}
        .header {{ text-align: center; margin-bottom: 20px; }}
        .card {{ background: white; border-radius: 12px; padding: 0; margin-bottom: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); overflow: hidden; }}
        .video-wrapper {{ position: relative; width: 100%; padding-top: 177.78%; /* 9:16 aspect ratio */ background: black; }}
        video {{ position: absolute; top: 0; left: 0; width: 100%; height: 100%; object-fit: cover; }}
        .info {{ padding: 15px; }}
        .title {{ font-weight: 600; font-size: 1.1em; margin-bottom: 5px; color: #1c1c1e; }}
        .meta {{ color: #8e8e93; font-size: 0.9em; margin-bottom: 15px; }}
        
        .btn {{ 
            display: block; width: 100%; text-align: center; 
            padding: 12px 0; border-radius: 8px; font-weight: 600; text-decoration: none; font-size: 16px;
            background-color: #007AFF; color: white; border: none; cursor: pointer;
        }}
        .btn:active {{ opacity: 0.8; }}
        
    </style>
</head>
<body>
    <div class="header">
        <h1>Replay Cam</h1>
        <p style="color: #666; font-size: 0.9rem;">Verbonden met "Replay" Wi-Fi</p>
    </div>

    <div id="video-list">
        {''.join([f'''
        <div class="card">
            <div class="video-wrapper">
                <video controls preload="metadata" playsinline>
                    <source src="/video/{v['name']}" type="video/mp4">
                </video>
            </div>
            <div class="info">
                <div class="title">{v['name']}</div>
                <div class="meta">{v['size']}</div>
                <a href="/video/{v['name']}?download=true" class="btn download-btn" onclick="handleDownload(event)">Download Video</a>
            </div>
        </div>
        ''' for v in videos])}
    </div>

</body>
</html>
"""
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(html.encode('utf-8'))


    def serve_instruction(self):
        # HTML in het Nederlands
        html = f"""
<!DOCTYPE html>
<html lang="nl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Replay Video's</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; background: #f2f2f7; margin: 0; padding: 15px; }}
        .header {{ text-align: center; margin-bottom: 20px; }}
        video {{ position: absolute; top: 0; left: 0; width: 100%; height: 100%; }}
        .info {{ padding: 15px; }}
        .title {{ font-weight: 600; font-size: 1.1em; margin-bottom: 5px; color: #1c1c1e; }}
        .meta {{ color: #8e8e93; font-size: 0.9em; margin-bottom: 15px; }}
        
        .btn {{ 
            display: block; width: 100%; text-align: center; 
            padding: 12px 0; border-radius: 8px; font-weight: 600; text-decoration: none; font-size: 16px;
            background-color: #007AFF; color: white; border: none; cursor: pointer;
        }}
        .btn:active {{ opacity: 0.8; }}
        
    </style>
</head>
<body>
    <div class="header">
        <h1>Replay Cam</h1>
        <p style="color: #666; font-size: 0.9rem;">Verbonden met "Replay" Wi-Fi</p>
    </div>

    <div id="ios-instruction">
        <div class="instruction-content">
            <h3 style="margin-top:0">⚠️ iOS Beveiliging</h3>
            <p>Apple blokkeert downloads in dit inlogscherm.</p>
            <div class="instruction-step">1. Tik rechtsboven op <b>Annuleer</b>.</div>
            <div class="instruction-step">2. Kies <b>Gebruik zonder internet</b>.</div>
            <div class="instruction-step">3. Open Safari en ga naar: <br><b style="font-size:1.3em; display:block; text-align:center; margin-top:5px; color:#007AFF;">{DOMAIN_NAME}</b></div>
        </div>
    </div>

</body>
</html>
"""
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(html.encode('utf-8'))

    def serve_video_file(self, path, is_download=False):
        filename = os.path.basename(path)
        file_path = os.path.join(RECORDINGS_DIR, filename)

        if not os.path.exists(file_path):
            self.send_error(404)
            return

        stat = os.stat(file_path)
        file_size = stat.st_size
        range_header = self.headers.get("Range")
        
        start = 0
        end = file_size - 1
        status = 200

        if range_header:
            status = 206
            bytes_range = range_header.replace("bytes=", "").split("-")
            start = int(bytes_range[0])
            if len(bytes_range) > 1 and bytes_range[1]:
                end = int(bytes_range[1])

        chunk_len = (end - start) + 1

        self.send_response(status)
        self.send_header("Content-type", "video/mp4")
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Range", f"bytes {start}-{end}/{file_size}")
        self.send_header("Content-Length", str(chunk_len))
        
        if is_download:
            self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
        
        self.end_headers()

        with open(file_path, "rb") as f:
            f.seek(start)
            bytes_sent = 0
            while bytes_sent < chunk_len:
                chunk = f.read(min(65536, chunk_len - bytes_sent))
                if not chunk: break
                try:
                    self.wfile.write(chunk)
                    bytes_sent += len(chunk)
                except BrokenPipeError:
                    break

    def format_size(self, size):
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024: return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"

if __name__ == "__main__":
    if not os.path.exists(RECORDINGS_DIR):
        os.makedirs(RECORDINGS_DIR)
    
    server = HTTPServer(("0.0.0.0", PORT), CaptiveHandler)
    print(f"Serving on port {PORT}...")
    server.serve_forever()
"""
/api/info  — fetch YouTube video metadata + available formats
Serverless safe: no threading, no disk writes, just metadata extraction.
"""
import json
import re
from http.server import BaseHTTPRequestHandler
import yt_dlp


def format_size(b):
    if not b:
        return "Unknown"
    for unit in ["B", "KB", "MB", "GB"]:
        if b < 1024:
            return f"{b:.1f} {unit}"
        b /= 1024
    return f"{b:.1f} GB"


def format_duration(s):
    if not s:
        return "0:00"
    s = int(s)
    if s < 3600:
        return f"{s // 60}:{s % 60:02d}"
    return f"{s // 3600}:{(s % 3600) // 60:02d}:{s % 60:02d}"


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length) or b"{}")
        url = body.get("url", "").strip()

        if not url:
            self._json({"error": "URL is required"}, 400)
            return

        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)

            formats = info.get("formats", [])
            video_formats = []
            audio_formats = []
            seen_v, seen_a = set(), set()

            for f in formats:
                vcodec = f.get("vcodec", "none")
                acodec = f.get("acodec", "none")
                height = f.get("height")
                abr = f.get("abr")
                ext = f.get("ext", "")
                fid = f.get("format_id", "")
                size = f.get("filesize") or f.get("filesize_approx")

                if vcodec != "none" and height:
                    key = (height, ext)
                    if key not in seen_v:
                        seen_v.add(key)
                        video_formats.append({
                            "format_id": fid,
                            "quality": f"{height}p",
                            "height": height,
                            "ext": ext,
                            "fps": f.get("fps"),
                            "filesize": format_size(size),
                            "has_audio": acodec != "none",
                            "vcodec": vcodec,
                        })

                elif acodec != "none" and vcodec == "none" and abr:
                    key = (int(abr), ext)
                    if key not in seen_a:
                        seen_a.add(key)
                        audio_formats.append({
                            "format_id": fid,
                            "quality": f"{int(abr)}kbps",
                            "abr": abr,
                            "ext": ext,
                            "filesize": format_size(size),
                        })

            video_formats.sort(key=lambda x: x["height"], reverse=True)
            audio_formats.sort(key=lambda x: x["abr"], reverse=True)

            self._json({
                "title": info.get("title", "Unknown"),
                "thumbnail": info.get("thumbnail", ""),
                "duration": format_duration(info.get("duration")),
                "channel": info.get("channel") or info.get("uploader", "Unknown"),
                "view_count": f"{info.get('view_count', 0):,}" if info.get("view_count") else "N/A",
                "video_id": info.get("id", ""),
                "video_formats": video_formats,
                "audio_formats": audio_formats,
            })

        except yt_dlp.utils.DownloadError as e:
            self._json({"error": str(e)}, 400)
        except Exception as e:
            self._json({"error": f"Unexpected error: {str(e)}"}, 500)

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def _json(self, data, status=200):
        body = json.dumps(data).encode()
        self.send_response(status)
        self._cors()
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

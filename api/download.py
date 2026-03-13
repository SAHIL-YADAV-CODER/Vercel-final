"""
/api/download  — extract a direct streamable/downloadable URL for a given format.
Serverless safe: no disk writes. Returns a signed stream URL that the browser
can follow directly with Content-Disposition: attachment.
"""
import json
from http.server import BaseHTTPRequestHandler
import yt_dlp


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length) or b"{}")

        url = body.get("url", "").strip()
        format_id = body.get("format_id", "")
        download_type = body.get("type", "video")   # "video" | "audio"
        audio_format = body.get("audio_format", "mp3")

        if not url:
            self._json({"error": "URL is required"}, 400)
            return

        try:
            # Build format selector
            if download_type == "audio":
                fmt = "bestaudio/best"
            else:
                if format_id:
                    fmt = f"{format_id}+bestaudio/{format_id}/best"
                else:
                    fmt = "bestvideo+bestaudio/best"

            ydl_opts = {
                "quiet": True,
                "no_warnings": True,
                "skip_download": True,
                "format": fmt,
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)

            # Find the best matching format's direct URL
            selected = None
            formats = info.get("formats", [])

            if format_id and download_type == "video":
                # Try exact match first
                for f in formats:
                    if f.get("format_id") == format_id:
                        selected = f
                        break

            if not selected:
                # Fall back to the resolved format
                selected = info  # top-level has the merged URL for bestvideo+bestaudio

            direct_url = selected.get("url") or info.get("url")
            ext = selected.get("ext", "mp4")
            title = info.get("title", "video")

            # Sanitize title for filename
            safe_title = "".join(c for c in title if c.isalnum() or c in " _-")[:80].strip()

            if download_type == "audio":
                filename = f"{safe_title}.{audio_format}"
                mime = "audio/mpeg" if audio_format == "mp3" else f"audio/{audio_format}"
            else:
                filename = f"{safe_title}.{ext}"
                mime = f"video/{ext}"

            # Also collect all format URLs for the proxy fallback
            format_urls = {}
            for f in formats:
                fid = f.get("format_id")
                if fid and f.get("url"):
                    format_urls[fid] = f["url"]

            self._json({
                "stream_url": direct_url,
                "filename": filename,
                "mime": mime,
                "ext": ext,
                "title": title,
                "format_urls": format_urls,
            })

        except yt_dlp.utils.DownloadError as e:
            self._json({"error": str(e)}, 400)
        except Exception as e:
            self._json({"error": f"Error: {str(e)}"}, 500)

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

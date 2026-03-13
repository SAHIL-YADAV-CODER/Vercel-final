from http.server import BaseHTTPRequestHandler
import json
import yt_dlp


def build_ydl_opts(extra={}):
    opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "extractor_args": {
            "youtube": {
                "player_client": ["tv_embedded", "android"],
                "player_skip": ["webpage", "config"],
            }
        },
        "http_headers": {
            "User-Agent": (
                "Mozilla/5.0 (ChromiumStylePlatform) Cobalt/Version"
            ),
        },
    }
    opts.update(extra)
    return opts


class handler(BaseHTTPRequestHandler):

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length) or b"{}")

        url = body.get("url", "").strip()
        format_id = body.get("format_id", "")
        download_type = body.get("type", "video")
        audio_format = body.get("audio_format", "mp3")

        if not url:
            return self._json({"error": "URL is required"}, 400)

        try:
            if download_type == "audio":
                fmt = "bestaudio/best"
            else:
                fmt = f"{format_id}+bestaudio/{format_id}/best" if format_id else "bestvideo+bestaudio/best"

            ydl_opts = build_ydl_opts({"format": fmt})

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)

            formats = info.get("formats", [])
            selected = None
            if format_id and download_type == "video":
                for f in formats:
                    if f.get("format_id") == format_id:
                        selected = f
                        break

            if not selected:
                selected = info

            direct_url = selected.get("url") or info.get("url")
            ext = selected.get("ext", "mp4")
            title = info.get("title", "video")
            safe_title = "".join(c for c in title if c.isalnum() or c in " _-")[:80].strip()

            if download_type == "audio":
                filename = f"{safe_title}.{audio_format}"
                mime = "audio/mpeg" if audio_format == "mp3" else f"audio/{audio_format}"
            else:
                filename = f"{safe_title}.{ext}"
                mime = f"video/{ext}"

            self._json({
                "stream_url": direct_url,
                "filename": filename,
                "mime": mime,
                "ext": ext,
                "title": title,
            })

        except yt_dlp.utils.DownloadError as e:
            err = str(e)
            if "Sign in" in err or "bot" in err.lower():
                self._json({
                    "error": "YouTube is blocking this request. Please try again in a moment."
                }, 429)
            else:
                self._json({"error": err}, 400)
        except Exception as e:
            self._json({"error": str(e)}, 500)

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

"""
/api/proxy  — streams a YouTube direct URL through Vercel so the browser
can download it with proper Content-Disposition headers (no CORS issues).
Streams in chunks to stay within Vercel's memory limits.
"""
import json
import urllib.request
import urllib.parse
from http.server import BaseHTTPRequestHandler


# YouTube requires a browser-like User-Agent
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

CHUNK = 1024 * 256  # 256KB chunks


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        # Parse query params: ?url=...&filename=...&mime=...
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)

        stream_url = params.get("url", [None])[0]
        filename = params.get("filename", ["download"])[0]
        mime = params.get("mime", ["application/octet-stream"])[0]

        if not stream_url:
            self._error("Missing url parameter", 400)
            return

        try:
            req = urllib.request.Request(
                stream_url,
                headers={
                    "User-Agent": UA,
                    "Referer": "https://www.youtube.com/",
                    "Accept": "*/*",
                    "Accept-Encoding": "identity",
                },
            )

            with urllib.request.urlopen(req, timeout=30) as resp:
                content_length = resp.headers.get("Content-Length", "")

                self.send_response(200)
                self.send_header("Content-Type", mime)
                self.send_header(
                    "Content-Disposition",
                    f'attachment; filename="{filename}"'
                )
                if content_length:
                    self.send_header("Content-Length", content_length)
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Cache-Control", "no-cache")
                self.end_headers()

                while True:
                    chunk = resp.read(CHUNK)
                    if not chunk:
                        break
                    self.wfile.write(chunk)

        except urllib.error.HTTPError as e:
            self._error(f"Upstream error: {e.code} {e.reason}", 502)
        except Exception as e:
            self._error(f"Proxy error: {str(e)}", 500)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.end_headers()

    def _error(self, msg, status):
        body = json.dumps({"error": msg}).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

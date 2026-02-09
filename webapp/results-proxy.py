#!/usr/bin/env python3
"""
Lightweight proxy for fetching ElevenLabs conversation analysis.
Runs on port 3001, proxied via nginx at /api/results/:id
"""

import http.server
import json
import os
import re
import urllib.request

API_KEY = os.environ["ELEVENLABS_API_KEY"]

class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        m = re.match(r"^/api/results/([a-zA-Z0-9_-]+)$", self.path)
        if not m:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'{"error":"not found"}')
            return

        cid = m.group(1)
        try:
            req = urllib.request.Request(
                f"https://api.elevenlabs.io/v1/convai/conversations/{cid}",
                headers={"xi-api-key": API_KEY}
            )
            resp = urllib.request.urlopen(req, timeout=10)
            data = json.loads(resp.read())

            result = {
                "conversationId": data.get("conversation_id"),
                "status": data.get("status"),
                "analysis": data.get("analysis")
            }

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(result).encode())
        except Exception as e:
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())

    def log_message(self, format, *args):
        pass  # Suppress request logs

if __name__ == "__main__":
    server = http.server.HTTPServer(("127.0.0.1", 3001), Handler)
    print("Results proxy running on port 3001")
    server.serve_forever()

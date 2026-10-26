#!/usr/bin/env python3
"""Serve build/ locally with correct Content-Type for extensionless pages.

Usage: python3 tools/serve_local.py [port]
The production site's pages have no extension (/visie, not /visie.html);
plain `python3 -m http.server` can't infer their type and sends
application/octet-stream, so browsers download instead of rendering.
"""
import http.server
import sys

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8000


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory="build", **kw)

    def guess_type(self, path):
        t = super().guess_type(path)
        if t in (None, "application/octet-stream"):
            return "text/html; charset=utf-8"
        return t


if __name__ == "__main__":
    print(f"erving build/ op http://localhost:{PORT}")
    http.server.test(Handler, port=PORT, bind="127.0.0.1")

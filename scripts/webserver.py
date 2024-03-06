from flask import Flask, Response, jsonify, send_from_directory
from scripts.helper.http import Extender
from typing import List, Callable, Tuple
from urllib.parse import urlparse
from pathlib import Path

class WebExtender(Extender):
    def register_paths(self,) -> List[Tuple[str, List[str], Callable]]:
        return [
            ("/script/<path:path>", ["GET"], self.script),
            ("/style/<path:path>", ["GET"], self.style),
            ("/media/<path:path>", ["GET"], self.media),
            ("/<path:path>", ["GET"], self.page)
        ]

    def script(self, path: str) -> Response:
        return send_from_directory(str(Path("static/web/script").absolute()), path)
    
    def style(self, path: str) -> Response:
        return send_from_directory(str(Path("static/web/style").absolute()), path)
    
    def media(self, path: str) -> Response:
        return send_from_directory(str(Path("static/web/media").absolute()), path)
    
    def page(self, path: str) -> Response:
        exclude = ["scripts/", "styles/", "media/"]

        if any([x and Path("static/web/" + path).is_file() in urlparse(path).path.split("/")[:-1] for x in exclude]):
            return "Invalid request", 400
        
        if not path.endswith(".html"):
            path += ".html"

        return send_from_directory(str(Path("static/web/").absolute()), path)
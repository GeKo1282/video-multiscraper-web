from flask import Flask, Response, jsonify, send_from_directory
from scripts.api import Extender
from typing import List, Callable, Union
from urllib.parse import urlparse
from pathlib import Path

class WebServer:
    def __init__(self) -> None:
        self._app = Flask(__name__)

    def add_path(self, route: str, methods: List[str], extender: Union[Extender, Callable]) -> None:
        self._app.route(route, methods=methods)(extender.handler if not callable(extender) else extender)

    def run(self, host: str, port: int) -> None:
        self._app.run(host=host, port=port)

    def register_paths(self) -> None:
        self.add_path("/script/<path:path>", ["GET"], self.script)
        self.add_path("/style/<path:path>", ["GET"], self.style)
        self.add_path("/media/<path:path>", ["GET"], self.media)

        self.add_path("/<path:path>", ["GET"], self.page)

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
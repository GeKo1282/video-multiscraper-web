from flask import Flask, Response, jsonify, send_from_directory
from scripts.helper.http import Extender
from scripts.helper.database import Database
from typing import List, Callable, Tuple
from urllib.parse import urlparse
from pathlib import Path

class WebExtender(Extender):
    def __init__(self, database: Database) -> None:
        self.database = database
        self.register_paths()

    def register_paths(self,) -> List[Tuple[str, List[str], Callable]]:
        return [
            ("/script/<path:path>", ["GET"], self.script),
            ("/style/<path:path>", ["GET"], self.style),
            ("/media/<path:path>", ["GET"], self.media),
            ("/login", ["GET"], self.login),
            ("/", ["GET"], self.app),
            ("/<path:path>", ["GET"], self.app),
            ("/cdn/user/<id>/avatar", ["GET"], self.avatar)
        ]

    def script(self, path: str) -> Response:
        return send_from_directory(str(Path("static/web/script").absolute()), path)
    
    def style(self, path: str) -> Response:
        return send_from_directory(str(Path("static/web/style").absolute()), path)
    
    def media(self, path: str) -> Response:
        return send_from_directory(str(Path("static/media").absolute()), path)
    
    def login(self) -> Response:
        return send_from_directory(str(Path("static/web/").absolute()), "login.html")
    
    def app(self, *args, **kwargs) -> Response:
        return send_from_directory(str(Path("static/web/").absolute()), "index.html")
    
    def page(self, path: str) -> Response:
        exclude = ["scripts/", "styles/", "media/"]

        if any([x and Path("static/web/" + path).is_file() in urlparse(path).path.split("/")[:-1] for x in exclude]):
            return "Invalid request", 400
        
        if not path.endswith(".html"):
            path += ".html"

        return send_from_directory(str(Path("static/web/").absolute()), path)
    
    def avatar(self, id: str) -> Response:
        image_data = self.database.select("users", ["image"], "id = ?", [id])

        if not image_data:
            return "Invalid request", 400
        
        return Response(image_data[0][0], mimetype="image/png")
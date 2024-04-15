from flask import Flask, Response, request, send_from_directory, redirect
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
            ("/cdn/user/<id>/avatar", ["GET"], self.avatar),
            ("/cdn/media/<content_id>/<resource>", ["GET"], self.cdn_media),
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
    
    def cdn_media(self, content_id: str, resource: str) -> Response:
        format = request.args.get("format", None)
        media_id = request.args.get("id", None)
        content = self.database.select("media", ["media_type", "media_format", "media_id", "origin_url", "data", "refers_to"], f"refer_id = ? AND media_name = ? {'AND media_format = ? ' if format else ''}{'AND media_id = ? ' if media_id else ''}", [content_id, resource, *([format] if format else []), *([media_id] if media_id else [])])

        if not content:
            return "Invalid request", 400
        
        while content[0][5]:
            new_content = self.database.select("media", ["media_type", "media_format", "media_id", "origin_url", "data", "refers_to"], f"id = ?", [content[0][5]])
            
            if not new_content:
                return "Invalid request", 400
            
            content = (
                content[0][0],
                content[0][1],
                content[0][2],
                content[0][3],
                new_content[0][4],
                new_content[0][5]
            )

        if not content[0][4]:
            return redirect(content[0][3])
        
        return Response(content[0][4], mimetype=f"{content[0][0]}/{content[0][1] if content[0][1] else 'plain'}")
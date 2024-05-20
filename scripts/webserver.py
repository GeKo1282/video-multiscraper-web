import json, asyncio
from flask import Flask, Response, request, send_from_directory, redirect, stream_with_context
from scripts.helper.http import Extender
from scripts.helper.database import Database
from scripts.helper.downloader import Downloader
from typing import List, Callable, Tuple, Dict
from urllib.parse import urlparse
from pathlib import Path

class WebExtender(Extender):
    def __init__(self, database: Database, downloader: Downloader) -> None:
        self.database: Database = database
        self.downloader: Downloader = downloader
        self._standard_chunksize: int = 1024 ** 2 # 1MB
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
            ("/cdn/media/<content_id>/<resource>", ["GET", "HEAD"], self.cdn_media),
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
    
    async def cdn_media(self, content_id: str, resource: str) -> Response:
        def generator(media_id, start = 0, end = -1):
            if end == -1:
                end = asyncio.run(self.downloader.get_content_size(media_id))

            while True:
                data = asyncio.run(self.downloader.request_instant(media_id, start, min(start + self._standard_chunksize - 1, end)))
                if not data:
                    continue

                yield data

                if (start >= end and end != -1) or (end == -1 and not data):
                    break
                
                start += self._standard_chunksize

        range_start, range_end = [*[int(x) for x in request.headers.get("Range", None).split("=")[1].split("-") if x], -1][:2] if "Range" in request.headers else [0, -1]
        format = request.args.get("format", None)
        media_id = request.args.get("id", None)
        token = request.args.get("token", None)
        content = self.database.select("media", ["id", "media_type", "media_format", "media_id", "metadata", "origin_url", "data_path", "refers_to", "requires_token"], f"refer_id = ? AND media_name = ? {'AND media_format = ? ' if format else ''}{'AND media_id = ? ' if media_id else ''}", [content_id, resource, *([format] if format else []), *([media_id] if media_id else [])])

        if not content:
            return "Invalid request", 400
        
        while content[0][6]:
            new_content = self.database.select("media", ["id", "media_type", "media_format", "media_id", "metadata", "origin_url", "data_path", "refers_to", "requires_token"], f"id = ?", [content[0][5]])
            
            if not new_content:
                return "Invalid request", 400
            
            content = (
                new_content[0][0],
                content[0][1],
                content[0][2],
                content[0][3],
                content[0][4],
                content[0][5],
                new_content[0][6],
                new_content[0][7],
                new_content[0][8]
            )

        if content[0][8]:
            if not token:
                return "Unauthorized", 401

            if not self.database.select("media_tokens", ["id"], "token = ? AND media_id = ?", [token, content[0][0]]):
                return "Unauthorized", 401
            
        if request.method == "HEAD":
            return Response(
                b"",
                status=200,
                headers={
                    "Accept-Ranges": "bytes",
                    "Content-Length": await self.downloader.get_content_size(content[0][0]),
                    "Content-Type": f"{content[0][1]}/{content[0][2] if content[0][2] else 'plain'}"
                }
            )

        if not content[0][6] and not json.loads(content[0][4]).get("source") == "cda":
            return redirect(content[0][5])
        
        return Response(
            generator(content[0][0], range_start, range_end),
            headers={
                "Accept-Ranges": "bytes",
                "Content-Type": f"{content[0][1]}/{content[0][2] if content[0][2] else 'plain'}",
                "Content-Length": range_end - range_start if range_end != -1 else await self.downloader.get_content_size(content[0][0]),
                **({
                    "Content-Range": f"bytes {range_start}-{range_end - 1 if range_end != -1 else await self.downloader.get_content_size(content[0][0]) - 1}/{await self.downloader.get_content_size(content[0][0])}",
                } if request.headers.get("Range", None) else {})
            },
            mimetype=f"{content[0][1]}/{content[0][2] if content[0][2] else 'plain'}",
            status=206 if request.headers.get("Range", None) else 200,
            direct_passthrough=True
        )
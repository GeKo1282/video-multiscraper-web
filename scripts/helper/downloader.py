import asyncio, json
from typing import Union, List, Tuple
from scripts.helper.database import Database
from scripts.helper.requester import Requester
from scripts.scrappers import Episode, Movie, Series, Service, OgladajAnime_pl

class Downloader:
    def __init__(self, database: Union[Database, str], services: List[Service], max_downloaders: int = 20) -> None:
        self.database: Database = database if isinstance(database, Database) else Database(database)
        self.services: List[Service] = services
        self.max_downloaders: int = max_downloaders

        self._controller_task: asyncio.Task = None
        self._tasks: List[asyncio.Task] = []
        self._queue: asyncio.Queue[Tuple[str, int, int]] = []

    async def start(self) -> None:
        # Is async to make sure that the downloader is started in the event loop
        self._controller_task = asyncio.create_task(self._controller())

        for _ in range(self.max_downloaders):
            self._tasks.append(asyncio.create_task(self._downloader()))

    async def request_instant(self, media_id: str, start: int, end: int) -> bytes:
        def cutout_ranges(original_range: Tuple[int, int], cutouts: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
            out_ranges = [original_range]

            for cutout in cutouts:
                collider = next((range for range in out_ranges if range[0] <= cutout[0] <= range[1] or range[0] <= cutout[1] <= range[1]), None) 
                if not collider:
                    continue

                if collider[0] <= cutout[0] and collider[1] >= cutout[1]:
                    out_ranges.remove(collider)
                    if cutout[0] - collider[0] > 0:
                        out_ranges.append((collider[0], cutout[0]))
                    
                    if collider[1] - cutout[1] > 0:
                        out_ranges.append((cutout[1], collider[1]))

                elif cutout[0] <= collider[0]:
                    out_ranges.remove(collider)
                    if collider[1] - cutout[1] > 0:
                        out_ranges.append((cutout[1], collider[1]))

                elif cutout[1] >= collider[1]:
                    out_ranges.remove(collider)
                    if cutout[0] - collider[0] > 0:
                        out_ranges.append((collider[0], cutout[0]))

            out_ranges.sort(key=lambda x: x[0])

            return out_ranges
        
        chunks = self.database.select("temporary_media_data", ["data", "start_byte", "end_byte"], "media_id = ? AND start_byte <= ? AND end_byte >= ? ORDER BY start_byte", [media_id, start, end])
        
        if end < start:
            raise ValueError("End byte is lower than start byte!")
        
        if start < 0:
            raise ValueError("Start byte is lower than 0!")

        if chunks:
            data_ranges = cutout_ranges((start, end), [(chunk[1], chunk[2]) for chunk in chunks])
            
            got_data: dict = {}

            for range in data_ranges:
                got_data[range] = await self.request_instant(media_id, range[0] + 1, range[1] - 1)

            for chunk in chunks:
                got_data[(start if chunk[1] <= start else chunk[1], end if chunk[2] >= end else chunk[2])] = chunk[0][0 if chunk[1] <= start else start - chunk[1]:end - chunk[1] + 1 if chunk[2] >= end else None]

            return b"".join([got_data[range] for range in sorted(got_data.keys(), key=lambda x: x[0])])
        
        media = self.database.select("media", ["refer_id", "origin_url", "metadata"], "id = ?", [media_id])

        if not media:
            raise ValueError("Media not found!")
        
        prefix_to_source = {
            "oa-": OgladajAnime_pl
        }

        service = next((service for service in self.services if media[0][0].startswith(next((prefix for prefix in prefix_to_source if isinstance(service, prefix_to_source[prefix])), None))), None)
        content: Union[Movie, Series, Episode] = service.get_by_uid(media[0][0])

        if not content:
            raise ValueError("Content not found!")
        
        data = await content.download(media_id, start, end, Requester.get_requester("cda.main"))

        if not self.database.select("temporary_media_data", ["id"], "media_id = ? AND start_byte = ? AND end_byte = ?", [media_id, start, start + len(data) - 1]):
            # Anti-simultaneous requests
            self.database.insert("temporary_media_data", [
                "media_id",
                "start_byte",
                "end_byte",
                "data",
            ], [
                media_id,
                start,
                start + len(data) - 1,
                data
            ])
            
        return data

    async def get_content_size(self, media_id: str) -> int:
        media = self.database.select("media", ["refer_id", "metadata", "media_id"], "id = ?", [media_id])

        if not media:
            raise ValueError("Media not found!")

        if media and media[0][1] and json.loads(media[0][1]).get("size"):
            return json.loads(media[0][1])["size"]
        
        prefix_to_source = {
            "oa-": OgladajAnime_pl
        }

        service = next((service for service in self.services if media[0][0].startswith(next((prefix for prefix in prefix_to_source if isinstance(service, prefix_to_source[prefix])), None))), None)
        content: Union[Movie, Series, Episode] = service.get_by_uid(media[0][0])

        if not content:
            raise ValueError("Content not found!")
        
        meta = await content.get_media_metadata(media[0][2], ["size"])

        if not meta:
            return 0
        
        return meta["size"]

    async def _controller(self) -> None:
        # In order to download a media following need to be fulfilled:
        # 1. Media should exist in the database
        # 2. Media should not be downloaded yet
        # 3. Media should not be in the queue / in process of downloading
        # 4. Media limit is not reached yet
        # 5. Media entry in the database should not be reffered by any other media (so the media won't duplicate)
        # 6. If media is partially inside temporary table it should be prioritized

        while True:
            await asyncio.sleep(1)

    async def _downloader(self) -> None:
        while True:
            media_id, url, start_byte, end_byte, meta = await self._queue.get(0)
            
            if json.loads(meta or "{}").get("source") == "cda":
                #requests.get("https://vwaw651.cda.pl/e/b/d/3ChVvlw9BUVkhmNR9KYAsA/339b/Znhvckc4SUdTQ1o5WUxzSFZBPT0/1713425351/hd0de242e7dd6b52aefa18522d125c9cd0.mp4", headers={"Referer": "https://vwaw651.cda.pl/e/b/d/3ChVvlw9BUVkhmNR9KYAsA/339b/Znhvckc4SUdTQ1o5WUxzSFZBPT0/1713425351/hd0de242e7dd6b52aefa18522d125c9cd0.mp4", "Cookie": "cda.player=html5", "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3", "Range": "bytes=0-1024"}).content
                data = await Requester.get_requester("cda.main").get(
                    url,
                    headers={
                        "Referer": url,
                        "Cookie": "cda.player=html5",
                        "Range": f"bytes={start_byte}-{end_byte - 1}"
                    }
                )

            self.database.insert("temporary_media_data", [
                    "uid",
                    "start_byte",
                    "end_byte",
                    "data",
                ], [
                    media_id,
                    start_byte,
                    end_byte,
                    data
                ])
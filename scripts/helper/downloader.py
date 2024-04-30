import asyncio, json, threading
from typing import Union, List, Tuple, Literal, Optional
from scripts.helper.database import Database
from scripts.helper.requester import Requester
from scripts.scrappers import Episode, Movie, Series, Service, OgladajAnime_pl
from scripts.helper.logger import Fore, Color

class Downloader:
    def __init__(self, database: Union[Database, str], services: List[Service], max_downloaders: int = 20) -> None:
        self.database: Database = database if isinstance(database, Database) else Database(database)
        self.services: List[Service] = services

        self.max_downloaders: int = max_downloaders
        self.priority_downloaders: int = 5

        self._tasks: List[asyncio.Task] = []
        self._task_flag: asyncio.Event = None
        self._downloader_loop: asyncio.AbstractEventLoop = None
        self._top_priority_queue: List[Tuple[str, int, int, int, Optional[Tuple[asyncio.Event, asyncio.AbstractEventLoop]]]] = []
        self._buffer_queue: List[Tuple[str, int, int, int, Optional[Tuple[asyncio.Event, asyncio.AbstractEventLoop]]]] = []
        self._queue: List[Tuple[str, int, int, int, Optional[Tuple[asyncio.Event, asyncio.AbstractEventLoop]]]] = []
        self._requests_in_progress: List[Tuple[str, int, int]] = []

        self._running: bool = False

    def set_flag_in_loop(self, flag: asyncio.Event, loop: asyncio.AbstractEventLoop) -> None:
        async def setter():
            flag.set()

        asyncio.run_coroutine_threadsafe(setter(), loop)

    def set_downloader_flag(self) -> None:
        async def setter():
            self._task_flag.set()

        asyncio.run_coroutine_threadsafe(setter(), self._downloader_loop)

    def start(self) -> None:
        threading.Thread(target=lambda: asyncio.run(self._downloader())).start()
        self._running = True

    def stop(self) -> None:
        self._running = False

    def queue_download(self, media_id: str, start: int, end: int, chunk_size: int, priority: Union[Literal["top"], Literal["buffer"], Literal["regular"]] = "regular", *, completed_flag: Tuple[asyncio.Event, asyncio.AbstractEventLoop] = None) -> Tuple[int, int, bytes]:
        {
            "top": self._top_priority_queue,
            "buffer": self._buffer_queue,
            "regular": self._queue
        }[priority].append((media_id, start, end, chunk_size, completed_flag))

        self.set_downloader_flag()

    async def request_instant(self, media_id: str, start: int, end: int, chunk_size: int = (1 * 1024 ** 2)) -> bytes:
        flag = asyncio.Event()
        
        self.queue_download(media_id, start, end, chunk_size, "top", completed_flag=(flag, asyncio.get_event_loop()))

        await flag.wait()

        out_data = b""
        chunks = self.database.select("temporary_media_data", ["start_byte", "end_byte", "data"], "media_id = ? AND (NOT start_byte > ? AND NOT end_byte < ?)", [media_id, end, start])
        print(f"Chunks colliding for {Fore.RED}{start}-{end}{Color.RESET}: {[(chunk[0], chunk[1]) for chunk in chunks]}")
        
        for chunk in chunks:
            print("Chunk:", chunk[0], chunk[1], "Returning from chunk:", start + len(out_data) - chunk[0], end + len(out_data) - chunk[0] + 1)
            out_data += chunk[2][start + len(out_data) - chunk[0]:end + len(out_data) - chunk[0] + 1]

        print("Retruning data:", start, end, len(out_data))

        return out_data

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

    async def _downloader(self) -> None:
        # In order to download a media following need to be fulfilled:
        # 1. Media should exist in the database
        # 2. Media should not be downloaded yet
        # 3. Media should not be in the queue / in process of downloading
        # 4. Media limit is not reached yet
        # 5. Media entry in the database should not be reffered by any other media (so the media won't duplicate)
        # 6. If media is partially inside temporary table it should be prioritized

        self._task_flag = asyncio.Event()
        self._downloader_loop = asyncio.get_event_loop()

        def cutout_ranges(original_range: Tuple[int, int], cutouts: List[Tuple[int, int]], start_inclusive: bool = False, end_inclusive: bool = False) -> List[Tuple[int, int]]:
            out_ranges = [original_range]

            for cutout in cutouts:
                collider = next((range for range in out_ranges if not cutout[0] > range[1] and not cutout[1] < range[0]), None) 
                if not collider:
                    continue

                if cutout[0] <= collider[0] and cutout[1] >= collider[1]:
                     out_ranges.remove(collider)

                elif collider[0] <= cutout[0] and collider[1] >= cutout[1]:
                    out_ranges.remove(collider)
                    if cutout[0] - collider[0] > 0:
                        out_ranges.append((collider[0] if start_inclusive else collider[0], cutout[0] if end_inclusive else cutout[0] - 1))
                    
                    if collider[1] - cutout[1] > 0:
                        out_ranges.append((cutout[1] if start_inclusive else cutout[1] + 1, collider[1] if end_inclusive else collider[1]))

                elif cutout[0] <= collider[0]:
                    out_ranges.remove(collider)
                    if collider[1] - cutout[1] > 0:
                        out_ranges.append((cutout[1] if start_inclusive else cutout[1] + 1, collider[1] if end_inclusive else collider[1]))

                elif cutout[1] >= collider[1]:
                    out_ranges.remove(collider)
                    if cutout[0] - collider[0] > 0:
                        out_ranges.append((collider[0] if start_inclusive else collider[0], cutout[0] if end_inclusive else cutout[0] - 1))

            out_ranges.sort(key=lambda x: x[0])

            return out_ranges
        
        downloader_tasks: List[asyncio.Task] = []

        async def download_chunk(media_id: str, start: int, end: int, flag: Tuple[asyncio.Event, asyncio.AbstractEventLoop] = None) -> bytes:
            nonlocal downloader_tasks

            media = self.database.select("media", ["refer_id"], "id = ?", [media_id])
            referer = self.database.select("content", ["source"], "uid = ?", [media[0][0]])

            service_class = {
                "ogladajanime": OgladajAnime_pl
            }[referer[0][0]]

            service = next((service for service in self.services if isinstance(service, service_class)), None)
            content: Union[Movie, Series, Episode] = service.get_by_uid(media[0][0])

            if not content:
                return b""
            
            data = await content.download(media_id, start, end, Requester.get_requester("cda.main"))

            self.database.insert("temporary_media_data", [
                "media_id",
                "start_byte",
                "end_byte",
                "data"
            ], [
                media_id,
                start,
                end,
                data
            ])

            self._requests_in_progress.remove((media_id, start, end))
            downloader_tasks.remove(asyncio.current_task())

            if flag:
                self.set_flag_in_loop(flag[0], flag[1])

            self.set_downloader_flag()

        while self._running:
            while all([not queue for queue in [self._top_priority_queue, self._buffer_queue, self._queue]]) or \
             (len(downloader_tasks) >= (self.max_downloaders - self.priority_downloaders) and not self._top_priority_queue) or \
             len(downloader_tasks) >= self.max_downloaders:
                await self._task_flag.wait()
                self._task_flag.clear()

            queue_type = "top_priority" if self._top_priority_queue else "buffer" if self._buffer_queue else "regular"
            media_id, start, end, chunk_size, flag = (self._top_priority_queue if self._top_priority_queue else self._buffer_queue if self._buffer_queue else self._queue)[0]

            if end - start > chunk_size:
                if queue_type == "top_priority":
                    self._top_priority_queue[0] = (media_id, start + chunk_size, end, chunk_size, flag)
                elif queue_type == "buffer":
                    self._buffer_queue[0] = (media_id, start + chunk_size, end, chunk_size, flag)
                else:
                    self._queue[0] = (media_id, start + chunk_size, end, chunk_size, flag)

                end = start + chunk_size
                flag = None

            colliding_chunks = self.database.select("temporary_media_data", ["start_byte", "end_byte"], "media_id = ? AND (NOT start_byte > ? AND NOT end_byte < ?)", [media_id, end, start])
            if colliding_chunks:
                cutouts = cutout_ranges((start, end), colliding_chunks)
                if not cutouts:
                    if queue_type == "top_priority":
                        del self._top_priority_queue[0]
                    elif queue_type == "buffer":
                        del self._buffer_queue[0]
                    else:
                        del self._queue[0]
                    if flag:
                        self.set_flag_in_loop(flag[0], flag[1])
                    continue
                
                new_queue_start = [(media_id, cutout[0], cutout[1], chunk_size, None) for cutout in cutouts]
                new_queue_start[-1] = (media_id, new_queue_start[-1][1], new_queue_start[-1][2], chunk_size, flag)
                if queue_type == "top_priority":
                    self._top_priority_queue = new_queue_start + self._top_priority_queue[1:]
                elif queue_type == "buffer":
                    self._buffer_queue = new_queue_start + self._buffer_queue[1:]
                else:
                    self._queue = new_queue_start + self._queue[1:]              
                continue
            
            colliding_requests = [request for request in self._requests_in_progress if request[0] == media_id and request[1] <= start <= request[2] or request[1] <= end <= request[2]]
            if colliding_requests:
                cutouts = cutout_ranges((start, end), [(request[1], request[2]) for request in colliding_requests])
                if not cutouts:
                    if queue_type == "top_priority":
                        del self._top_priority_queue[0]
                    elif queue_type == "buffer":
                        del self._buffer_queue[0]
                    else:
                        del self._queue[0]

                    if flag:
                        self.set_flag_in_loop(flag[0], flag[1])

                    continue

                new_queue_start = [(media_id, cutout[0], cutout[1], chunk_size, None) for cutout in cutouts]
                new_queue_start[-1] = (media_id, new_queue_start[-1][1], new_queue_start[-1][2], chunk_size, flag)
                if queue_type == "top_priority":
                    self._top_priority_queue = new_queue_start + self._top_priority_queue[1:]
                elif queue_type == "buffer":
                    self._buffer_queue = new_queue_start + self._buffer_queue[1:]
                else:
                    self._queue = new_queue_start + self._queue[1:]
                continue

            self._requests_in_progress.append((media_id, start, end))
            downloader_tasks.append(asyncio.create_task(download_chunk(media_id, start, end, flag)))

            if queue_type == "top_priority":
                del self._top_priority_queue[0]
            elif queue_type == "buffer":
                del self._buffer_queue[0]
            else:
                del self._queue[0]
import asyncio, json, bs4, html, re, pathlib
from bs4 import BeautifulSoup
from asyncio import Task
from typing import Optional, List, Tuple, Union, Literal, Self, Dict, Coroutine
from datetime import datetime
from urllib.parse import quote as urlquote, unquote as urlunquote, urlsplit, urlunsplit
from scripts.helper.requester import Requester
from scripts.helper.database import Database
from scripts.helper.util import sanitize, normalize, deduplicate

class Service:
    def __init__(self, *args, requester: Requester = None, **kwargs) -> None:
        self.codenames: List[str] = []
        self.base_url: str = None
        self.homepage_url: str = None
        self.search_suggestions_url: str = None

        self.logo_url: str = "/media/unknown-logo.png"
        self.icon_url: str = "/media/unknown-icon.png"

        self.default_headers: dict = {}

        self.requester: Requester = requester or Requester(default_headers={
            "Referer": self.base_url,
            "X-Requested-With": "XMLHttpRequest"
        }, max_requests_per_minute=20, max_requests_per_second=20)

    def get_by_uid(self, uid: str, get_similar: bool = False, get_episodes: bool = False, series: "Series" = None) -> Union["Series", "Movie", "Episode"]:
        '''
            This method is intended to be overwritten by devired classes.
        '''

    async def get_search_suggestions(self, hint: str = None, limit: int = 10, *, user_agent: Optional[str] = None, headers: Optional[dict] = None) -> List[str]:
        '''
            This method is intended to be overwritten by devired classes.
        '''

    async def get_homepage_suggestions(self) -> List[str]:
        '''
            This method is intended to be overwritten by devired classes.
        '''

    async def search(self, query: str) -> List[Union["Movie", "Series"]]:
        '''
            This method is intended to be overwritten by devired classes.
        '''

    def info(self, type: Union[Literal['printable'], Literal['JSON']] = "JSON") -> dict:
        if type.lower() == "json":
            return {
                "base_url": self.base_url,
                "homepage_url": self.homepage_url,
                "search_suggestions_url": self.search_suggestions_url,
                "logo_url": self.logo_url,
                "icon_url": self.icon_url
            }

        return f"Base URL: {self.base_url}\n" +\
         f"Homepage URL: {self.homepage_url}\n" +\
         f"Search Suggestions URL: {self.search_suggestions_url}" +\
         f"Logo URL: {self.logo_url}\n" +\
         f"Icon URL: {self.icon_url}"

class Movie:
    def __init__(self, url: str, uid: str, service: Service, title: str = None, thumbnail: str = None, description: str = None,
     genres: List[str] = None, release_year: int = None, duration: str = None, rating: float = None,
     director: str = None, actors: List[str] = None, trailer_url: str = None, similar: List["Movie"] = None, *args, requester: Requester = None, **kwargs) -> None:
        self.url: str = url
        self.uid: str = uid
        self.service: Service = service
        self.is_scrapped: bool = False if not all([
            title, thumbnail, description, genres, release_year, duration, rating, director, actors, trailer_url
        ]) else True

        self.title: str = title
        self.thumbnail: str = thumbnail
        self.description: str = description
        self.genres: List[str] = genres or []
        self.release_year: int = release_year
        self.duration: str = duration
        self.rating: float = rating
        self.director: str = director

        self.similar: List[Union[Series, Movie]] = similar or []

        self.requester: Requester = requester or Requester(default_headers={
            "Referer": self.url.split("://")[0] + "://" + self.url.split("://")[1].split("/")[0] + "/",
            "X-Requested-With": "XMLHttpRequest"
        }, max_requests_per_minute=20, max_requests_per_second=20)

    async def scrape(self) -> None:
        '''
            This method is intended to be overwritten by devired classes.
        '''

    async def get_sources(self) -> List[str]:
        '''
            This method is intended to be overwritten by devired classes.
        '''

    def info(self, type: Union[Literal['printable'], Literal['JSON']] = "JSON") -> dict:
        if type.lower() == "json":
            return {
                "url": self.url,
                "uid": self.uid,
                "title": self.title,
                "type": "movie",
                "thumbnail": self.thumbnail,
                "description": self.description,
                "genres": self.genres,
                "release_year": self.release_year,
                "duration": self.duration,
                "rating": self.rating,
                "director": self.director,
                "similar": [similar.url for similar in self.similar],
                "service": self.service.codenames[0]
            }
        
        return f"URL: {self.url}\n" +\
            f"UID: {self.uid}\n" +\
            f"Title: {self.title}\n" +\
            f"Thumbnail: {self.thumbnail}\n" +\
            f"Description: {self.description}\n" +\
            f"Genres: {', '.join(self.genres)}\n" +\
            f"Release Year: {self.release_year}\n" +\
            f"Duration: {self.duration}\n" +\
            f"Rating: {self.rating}\n" +\
            f"Director: {self.director}\n" +\
            f"Actors: {', '.join(self.actors)}\n" +\
            f"Similar: {', '.join([movie.url for movie in self.similar])}"

class Series:
    def __init__(self, url: str, uid: str, service: Service, title: str = None, thumbnail: str = None, description: str = None,
     genres: List[str] = None, release_time: Tuple[Union[datetime, int], Union[datetime, int]] = None,
     episodes: Union[dict[str, List["Episode"]], List["Episode"]] = None, 
     similar: List[Union["Series", "Movie"]] = None, *args, requester: Requester = None, **kwargs) -> None:
        
        self.url: str = url
        self.uid: str = uid
        self.service: Service = service
        self.is_scrapped: bool = False if not all([
            url, uid, title, thumbnail, description, genres, release_time, episodes
        ]) else True

        self.title: str = title
        self.thumbnail: str = thumbnail
        self.description: str = description
        self.genres: List[str] = genres or []
        self.release_time: Tuple[Union[datetime, int], Optional[Union[datetime, int]]] = (release_time[0] if type(release_time[0]) == datetime else datetime.fromtimestamp(release_time[0]), (release_time[1] if type(release_time[1]) == datetime else datetime.fromtimestamp(release_time[1])) if release_time[1] else None) if release_time else None
        self.episodes: Union[dict[str, List[Episode]], List[Episode]] = episodes or []

        self.similar: List[Union[Series, Movie]] = similar or []
        
        self.requester: Requester = requester or Requester(default_headers={
            "Referer": self.url.split("://")[0] + "://" + self.url.split("://")[1].split("/")[0] + "/",
            "X-Requested-With": "XMLHttpRequest"
        }, max_requests_per_minute=20, max_requests_per_second=20)

    async def scrape(self) -> None:
        '''
            This method is intended to be overwritten by devired classes.
        '''

    async def get_sources(self) -> List[str]:
        '''
            This method is intended to be overwritten by devired classes.
        '''

    def info(self, type: Union[Literal['printable'], Literal['JSON']] = "JSON", get_full_similar: bool = False, get_full_episodes: bool = False) -> dict:
        if type.lower() == "json":
            return {
                "url": self.url,
                "uid": self.uid,
                "title": self.title,
                "thumbnail": self.thumbnail,
                "type": "series",
                "description": self.description,
                "genres": self.genres,
                "release_time": [int(self.release_time[0].timestamp()), (int(self.release_time[1].timestamp()) if self.release_time[1] else None)] if self.release_time else None,
                "episodes": [episode.uid for episode in self.episodes] if not get_full_episodes else [episode.info() for episode in self.episodes],
                "similar": [similar.uid for similar in self.similar] if not get_full_similar else [similar.info("JSON", False, False) for similar in self.similar],
                "service": self.service.codenames[0]
            }
        
        return f"URL: {self.url}\n" +\
            f"UID: {self.uid}\n" +\
            f"Title: {self.title}\n" +\
            f"Thumbnail: {self.thumbnail}\n" +\
            f"Description: {self.description}\n" +\
            f"Genres: {', '.join(self.genres)}\n" +\
            f"Release Time: {self.release_time[0].strftime('%Y-%m-%d %H:%M:%S')} - {self.release_time[1].strftime('%Y-%m-%d %H:%M:%S')}\n" +\
            f"Episodes: {', '.join([episode.title for episode in self.episodes])}"

class Episode:
    def __init__(self, url: str, uid: str, series: Series, title: str = None, thumbnail: str = None, release_date: datetime = None,
        duration: str = None, description: str = None, *args, requester: Requester = None, **kwargs) -> None:
        self.url: str = url
        self.uid: str = uid
        self.is_scrapped: bool = False if not all([
            title, thumbnail, release_date, duration, description
        ]) else True

        self.title: str = title
        self.thumbnail: str = thumbnail
        self.release_date: datetime = release_date
        self.duration: str = duration
        self.description: str = description

        self.requester: Requester = requester or Requester(default_headers={
            "Referer": self.url.split("://")[0] + "://" + self.url.split("://")[1].split("/")[0] + "/",
            "X-Requested-With": "XMLHttpRequest"
        }, max_requests_per_minute=20, max_requests_per_second=20)
        
    async def scrape(self) -> None:
        '''
            This method is intended to be overwritten by devired classes.
        '''

    async def get_sources(self) -> List[str]:
        '''
            This method is intended to be overwritten by devired classes.
        '''

    async def get_media_metadata(self, media_id: str) -> dict:
        '''
            This method is intended to be overwritten by devired classes.
        '''

    def info(self, type: Union[Literal['printable'], Literal['JSON']] = "JSON") -> dict:
        if type.lower() == "json":        
            return {
                "url": self.url,
                "uid": self.uid,
                "title": self.title,
                "thumbnail": self.thumbnail,
                "release_date": self.release_date.timestamp() if self.release_date else None,
                "duration": self.duration,
                "description": self.description
            }
        
        return f"URL: {self.url}\n" +\
            f"Title: {self.title}\n" +\
            f"Thumbnail: {self.thumbnail}\n" +\
            f"Release Date: {self.release_date.strftime('%Y-%m-%d %H:%M:%S')}\n" +\
            f"Duration: {self.duration}\n" +\
            f"Description: {self.description}"

class SourceExtractor:
    @classmethod
    async def scrape(cls, url: str, headers: dict = None, *args,
     requester_id: str = "main", **kwargs) -> Tuple[str, List[Union[Tuple[Dict, str], str]]]:
        '''
            Intended to be overwritten by subclasses.
        '''

    @staticmethod
    def extract_m3u8(url: str, contents: str) -> Tuple[str, List[Tuple[dict, str]]]:
        def extract_properties(string: str) -> dict:
            properties = {}
            current_key = ""
            current_property = ""
            onkey = True
            escaped = False
            for character in string:
                if character == "\"":
                    escaped = not escaped
                    continue

                if character == "=" and not escaped:
                    onkey = False
                    continue

                if onkey:
                    current_key += character
                    continue

                if character == "," and not escaped:
                    properties[current_key] = current_property
                    current_key = ""
                    current_property = ""
                    onkey = True
                    continue

                current_property += character

            properties[current_key] = current_property

            return {key.lower().replace("-", ""): value for key, value in properties.items()}

        file_type = "index"
        lines = []
        for index, line in enumerate(contents.split("\n")):
            if line.startswith("#EXT-X-STREAM-INF"):
                file_type = "playlist"
            
            if line.startswith("#EXT-X-STREAM-INF"):
                property_list = extract_properties(line.replace("#EXT-X-STREAM-INF:", ""))
                lines.append(({
                    "bandwidth": property_list.get('bandwidth'),
                    "resolution": property_list.get('resolution'),
                    "framerate": property_list.get('framerate'),
                    "codecs": property_list.get('codecs'),
                }, contents.split("\n")[index + 1]))

            if file_type != "playlist" and not line.startswith("#"):
                lines.append(line)

        return file_type, lines

    @staticmethod
    def pythonize_json_string(string: str) -> dict:
        string = string.replace("'", '"')
        string = string[1:] if string.startswith("{") else string
        string = string[:-1] if string.endswith("}") else string
        out_dict = {}
        current_key = ""
        current_value = ""
        onkey = True
        escaped = False
        for char in string:
            if char == '"':
                escaped = not escaped
                continue

            if char == ":" and not escaped:
                onkey = False
                continue

            if onkey:
                current_key += char
                continue

            if char == "," and not escaped:
                out_dict[current_key] = current_value
                current_key = ""
                current_value = ""
                onkey = True
                continue

            current_value += char

        out_dict[current_key] = current_value

        return {key: value for key, value in out_dict.items()}

class CDA(SourceExtractor):
    def __init__(self) -> None:
        pass

    @staticmethod
    async def source_extractor(url: str, proxy = None, *, get_all_qualities: bool = False, get_top_quality: bool = True,
     get_quality_info: bool = True, prefer_quality: Union[int, str] = None) -> Dict[str, str]:
        
        async def get_sources(urllist: Union[List[Tuple[str, Optional[Union[str, int]]]], Tuple[str, Optional[Union[str, int]]]]):
            if not isinstance(urllist, list):
                urllist = [urllist]

            for url, quality in urllist:
                if type(quality) is int:
                    quality = str(quality)

                if quality and not quality.endswith("p"):
                    quality += "p"

                if quality:
                    new_url = list(urlsplit(url))
                    new_url[3] = "&wersja=" + quality
                    new_url = urlunsplit(new_url)

                urllist[urllist.index((url, quality))] = new_url if quality else url

            cookie = {
                "cda.player": "html5",
            }
            
            headers = {
                "Cookie": "; ".join([f"{key}={value}" for key, value in cookie.items()])
            }

            requests: List[Coroutine] = []

            for url in urllist:
                requests.append(Requester.get_requester('cda.main').get(url, headers=headers, proxies=({"http": proxy} if proxy else None)))

            responses = await asyncio.gather(*requests)

            return [r['text'] for r in responses]
                 
        def get_playerdata(soup: BeautifulSoup) -> dict:
            return json.loads(html.unescape(soup.find("div", id=re.compile(r"^mediaplayer.*$")).get("player_data")))['video']
        
        def decrypt_file(a):    
            for p in ('_XDDD', '_CDA', '_ADC', '_CXD', '_QWE', '_Q5', '_IKSDE'):
                a = a.replace(p, '')
            a = urlunquote(a)
            b = []
            for c in a:
                f = c if type(c) is int else ord(c)
                b.append(chr(33 + (f + 14) % 94) if 33 <= f <= 126 else chr(f))
            a = ''.join(b)
            a = a.replace('.cda.mp4', '')
            for p in ('.2cda.pl', '.3cda.pl'):
                a = a.replace(p, '.cda.pl')
            if '/upstream' in a:
                a = a.replace('/upstream', '.mp4/upstream')
                return 'https://' + a
            return 'https://' + a + '.mp4'

        if not any(url.replace("https://", "").replace("http://", "").replace("www.", "").startswith(prefix) for prefix in ["cda.pl", "ebd.cda.pl", "embed.cda.pl"]):
            return
        
        soup = BeautifulSoup((await get_sources((url, prefer_quality)))[0], "html.parser")
        playerdata = get_playerdata(soup)
        
        quality_dict: Dict[str, str] = {(str(key) + "p"): playerdata['qualities'][(str(key) + "p")] for key in list(reversed(sorted([int(key.replace("p", "")) for key in playerdata['qualities'].keys()])))}
        quality_dict[list(quality_dict.keys())[list(quality_dict.values()).index(playerdata['quality'])]] =  decrypt_file(playerdata['file'])

        requests = []

        if get_all_qualities:
            requests = []

            for quality in quality_dict.keys():
                if quality in quality_dict.keys() and any(quality_dict[quality].startswith(prefix) for prefix in ["https://", "http://"]):
                    continue

                requests.append((url, quality))

            responses = get_sources(requests)

            for response in responses:
                playerdata = get_playerdata(BeautifulSoup(response, "html.parser"))
                quality_dict[list(quality_dict.keys())[list(quality_dict.values()).index(playerdata['quality'])]] = decrypt_file(playerdata['file'])

        if get_top_quality:
            top_quality = list(quality_dict.keys())[0]
            if top_quality not in list(quality_dict.keys()) or not any(quality_dict[top_quality].startswith(prefix) for prefix in ["https://", "http://"]):
                quality_dict[top_quality] = decrypt_file(get_playerdata(BeautifulSoup(get_sources((url, top_quality))[0], "html.parser"))['file'])
            
        qualities = list(quality_dict.keys())

        quality_dict = {key: value for key, value in quality_dict.items() if any(value.startswith(prefix) for prefix in ["https://", "http://"])}

        return {**quality_dict, "duration": int(playerdata['duration']), **({"qualities": qualities} if get_quality_info else {})}


class OA_Movie(Movie):
    def __init__(self, url: str, uid: str, service: "OgladajAnime_pl", id: int = None, pegi: str = None, alternate_titles: List[str] = None,
         tags: List['str'] = None, views: int = None, rating: float = None, length: int = None,
         trailer_url: str = None, *args, **kwargs) -> None:
        super().__init__(url, uid, service, *args, **kwargs)

        self.id: int = id
        self.service: "OgladajAnime_pl" = service
        self.pegi: str = pegi
        self.alternate_titles: List[str] = alternate_titles or []
        self.tags: List[str] = tags or []
        self.views: int = views
        self.rating: float = rating
        self.length: int = length
        self.trailer_url: str = trailer_url

    async def scrape(self, *args) -> None:
        pass

    def info(self, type: Union[Literal['printable'], Literal['JSON']] = "JSON", *args, **kwargs) -> dict:
        if type.lower() == "json":
            return {
                **super().info("JSON"),
                "id": self.id,
                "pegi": self.pegi,
                "alternate_titles": self.alternate_titles,
                "tags": self.tags,
                "views": self.views,
                "rating": self.rating,
                "length": self.length,
                "trailer_url": self.trailer_url
            }
        
        return super().info("printable") + f"ID: {self.id}"

class OA_Series(Series):
    def __init__(self, url: str, uid: str, service: "OgladajAnime_pl", id: int = None, series_type: str = None, pegi: str = None, alternate_titles: List[str] = None,
         tags: List['str'] = None, views: int = None, rating: float = None, episode_count: int = None, episode_length: int = None,
         trailer_url: str = None, status: str = None, *args, **kwargs) -> None:
        super().__init__(url, uid, service, *args, **kwargs)

        if any([not id, not series_type, not pegi, not views, not rating, not status]):
            self.is_scrapped = False

        self.id: int = id
        self.service: "OgladajAnime_pl" = service
        self.series_type: str = series_type
        self.pegi: str = pegi
        self.alternate_titles: List[str] = alternate_titles or []
        self.tags: List[str] = tags or []
        self.views: int = views
        self.rating: float = rating
        self.episode_count: int = episode_count
        self.episode_length: int = episode_length
        self.trailer_url: str = trailer_url
        self.status: str = status

    async def scrape(self, scrape_similar: bool = True) -> Union[OA_Movie, Self]:
        data = f"id={self.id}"
        soup = bs4.BeautifulSoup(json.loads((await self.requester.post(self.service.anime_url, headers={
            "Content-Length": str(len(data)),
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Referer": self.url,
        }, data=data, allow_redirects=False))['text'])['data'], "html.parser")

        meta_container = soup.find("h4", attrs={"id": "anime_name_id"}).parent

        self.title = sanitize(meta_container.find("h4", attrs={"id": "anime_name_id"}).text)
        self.alternate_titles = meta_container.find("i").text.split("|")
        self.series_type, self.pegi, views = [sanitize(element.text) for element in meta_container.find("div").find_all("span")]
        self.views = int(views.replace(" ", ""))
        self.description = sanitize(meta_container.find("p").text.replace("<br>", "<newline>").replace("<br/>", "<newline>").replace("\n", "<newline>"))
        episode_count, episode_time, status, emission_start, emission_end = [*[sanitize(container.text.replace(container.find("b").text, "")) for container in meta_container.find_all("div", recursive=False)[-1].find("div").find_all("p", recursive=False)], None][:5]
        self.episode_count = int(episode_count)
        self.episode_length = int(episode_time.split(" ")[0]) * 60
        self.status = sanitize(status)
        self.release_time = (datetime.strptime(emission_start, "%Y-%m-%d"), (datetime.strptime(emission_end, "%Y-%m-%d") if status == "Zakończone" and emission_end else None))
        self.genres = [sanitize(element.text) for element in meta_container.find_all("div", recursive=False)[-1].find_all("div", class_="col-12", recursive=False)[1].find_all("div", class_="col-12")[0].find_all("span")[1:]]
        self.tags = [sanitize(element.text) for element in meta_container.find_all("div", recursive=False)[-1].find_all("div", class_="col-12", recursive=False)[1].find_all("div", class_="col-12")[1].find_all("span")[1:]]
        self.thumbnail = soup.find("img", attrs={"alt": self.title})["data-srcset"].split(" ")[0]
        self.rating = float(sanitize(soup.find("h4", class_="col-6").text.split("/")[0]))

        self.thumbnail = self.service.store_media(self.thumbnail, self, "thumbnail")

        similars: List[OA_Series, OA_Movie] = []
        tasks: List[Task] = []
        for similar in soup.find("div", id="similar_animes").find_all("div", class_="card-body"):
            async def scrape(similar: Union[OA_Series, OA_Movie]):
                if scrape_similar:
                    await similar.scrape(False)


                in_db = bool(self.service._database.select("content", ["uid"], "uid = ?", [similar.uid]))
                if in_db and not scrape_similar:
                    return
                
                content_info = similar.info("JSON")
                (self.service._database.update if in_db else
                self.service._database.insert)("content", [
                    "uid",
                    "origin_url",
                    "searchable",
                    "source",
                    "weight",
                    "type",
                    "title",
                    "meta"
                ], [
                    similar.uid,
                    similar.url,
                    True,
                    "ogladajanime",
                    1,
                    stype,
                    similar.title,
                    json.dumps({key:content_info[key] for key in content_info if key not in ["uid", "title", "url"]})
                ], **({
                    "where": "uid = ?",
                    "where_values": [similar.uid]
                } if in_db else {}))

            if len(similar.find_all("a")) < 2:
                continue

            a, a2 = similar.find_all("a")
            srating, spegi, stype = [element.text for element in similar.find_all("div", recursive=True)[-1].find_all("span")]
            similars.append((OA_Movie if stype == "movie" else OA_Series)(
                uid = f"oa-{int(a2.find('div')['title'])}",
                id = int(a2.find("div")["title"]),
                url = self.service.base_url + a2["href"],
                title = a2.find("div").text,
                thumbnail = a.find("img")["data-srcset"].split(" ")[0],
                rating = float(srating),
                pegi = spegi,
                service=self.service,
                **({
                    "series_type": stype
                } if stype != "movie" else {})
            ))

            tasks.append(asyncio.create_task(scrape(similars[-1])))

        if tasks:
            await asyncio.wait(tasks, return_when=asyncio.ALL_COMPLETED)

        self.similar = similars

        episodes: List[OA_Episode] = []
        for episode in soup.find("ul", id="ep_list").find_all("li"):
            # TODO: Sometimes, if episodes are not yet released, they are empty. Should be handled.
            # Sometimes OVAs or ONAs are mistaken for series, when in reality they are movies.
            #   Can be (kind of) easily handled, because when that happens the episode index is "Movie".
            if str(episode["value"]).lower() == "movie":
                new_content = OA_Movie(
                    url=self.url,
                    uid=self.uid,
                    service=self.service,
                    id=self.id,
                    pegi=self.pegi,
                    alternate_titles=self.alternate_titles,
                    tags=self.tags,
                    views=self.views,
                    rating=self.rating,
                    length=self.episode_length,
                    trailer_url=self.trailer_url,
                    title=self.title,
                    requester=self.requester
                )

                await new_content.scrape()
                return new_content

            episodes.append(OA_Episode(
                id=episode["ep_id"],
                uid=f"oa-{episode['ep_id']}",
                url=self.url.removesuffix("/") + "/" + episode["value"],
                index=float(episode["value"]),
                title=sanitize(episode["title"]),
                lang=episode.find("img")['alt'] if episode.find("img") else "unknown",
                service=self.service,
                series=self,
                requester=self.requester
            ))

            in_db = bool(self.service._database.select("content", ["uid"], "uid = ?", [episodes[-1].uid]))
            content_info = episodes[-1].info("JSON")
            (self.service._database.update if in_db else
            self.service._database.insert)("content", [
                "uid",
                "origin_url",
                "searchable",
                "source",
                "weight",
                "type",
                "title",
                "meta"
            ], [
                episodes[-1].uid,
                episodes[-1].url,
                True,
                "ogladajanime",
                .6,
                "episode",
                episodes[-1].title,
                json.dumps({key:content_info[key] for key in content_info if key not in ["uid", "title", "url"]})
            ], **({
                "where": "uid = ?",
                "where_values": [episodes[-1].uid]
            } if in_db else {}))

        self.episodes = episodes
        self.is_scrapped = True

        in_db = bool(self.service._database.select("content", ["uid"], "uid = ?", [self.uid]))        
        content_info = self.info("JSON")
        (self.service._database.update if in_db else
        self.service._database.insert)("content", [
            "uid",
            "origin_url",
            "searchable",
            "source",
            "weight",
            "type",
            "title",
            "meta"
        ], [
            self.uid,
            self.url,
            True,
            "ogladajanime",
            1,
            "series",
            self.title,
            json.dumps({key:content_info[key] for key in content_info if key not in ["uid", "title", "url"]})
        ], **({
            "where": "uid = ?",
            "where_values": [self.uid]
        } if in_db else {}))

        return self  

    def info(self, type: Union[Literal['printable'], Literal['JSON']] = "JSON", get_full_similar: bool = False, get_full_episodes: bool = False) -> dict:
        if type.lower() == "json":
            return {
                **super().info("JSON", get_full_similar, get_full_episodes),
                "id": self.id,
                "series_type": self.series_type,
                "pegi": self.pegi,
                "alternate_titles": self.alternate_titles,
                "tags": self.tags,
                "views": self.views,
                "rating": self.rating,
                "episode_length": self.episode_length,
                "trailer_url": self.trailer_url,
                "status": self.status
            }
        
        return super().info("printable", get_full_similar) + f"ID: {self.id}\n" +\
         f"Type: {self.type}"


class OA_Source:
    def __init__(self, uid: str, id: str, url: str, prefetch_url: str, audio_lang: str, sub_lang: str, source: str, quality: str, subber: str) -> None:
        self.uid: str = uid
        self.id: str = id
        self.url: str = url
        self.prefetch_url: str = prefetch_url
        self.audio_lang: str = audio_lang
        self.sub_lang: str = sub_lang
        self.source: str = source
        self.quality: str = quality
        self.subber: str = subber

    def info(self, type: Literal['printable'] | Literal['JSON'] = "JSON") -> dict:
        if type.lower() == "json":
            return {
                "uid": self.uid,
                "id": self.id,
                "url": self.url,
                "prefetch_url": self.prefetch_url,
                "audio_lang": self.audio_lang,
                "sub_lang": self.sub_lang,
                "source": self.source,
                "quality": self.quality,
                "subber": self.subber
            }
        
        return f"UID: {self.uid}\n" +\
            f"ID: {self.id}\n" +\
            f"URL: {self.url}\n" +\
            f"Prefetch URL: {self.prefetch_url}\n" +\
            f"Audio Language: {self.audio_lang}\n" +\
            f"Sub Language: {self.sub_lang}\n" +\
            f"Source: {self.source}\n" +\
            f"Quality: {self.quality}\n" +\
            f"Subber: {self.subber}"

class OA_Episode(Episode):
    def __init__(self, url: str, uid: str, id: str, index: int, series: OA_Series, title: str, lang: str,
        duration: str = None, sources: List[OA_Source] = None, qualities: List[str] = None, *args, requester: Requester, **kwargs) -> None:
        super().__init__(url, uid, series, title, None, None, duration, None, *args, requester=requester, **kwargs)

        self.index: int = index
        self.id: str = id
        self.series: OA_Series = series
        self.lang: str = lang
        self.sources: List[OA_Source] = [source if isinstance(source, OA_Source) else OA_Source(**source) for source in sources or []]
        self.qualities: List[str] = qualities or deduplicate([source.quality for source in self.sources])

    async def get_media_metadata(self, media_id: str, require_fields: List[str] = None) -> dict:
        media = self.series.service._database.select("media", ["origin_url", "metadata"], "media_id = ?", [media_id])

        if not media:
            return
        
        if media[0][1] and all([key in media[0][1] for key in (require_fields or ["url", "audio_lang", "sub_lang", "source", "quality", "subber", "size", "duration"])]):
            return json.loads(media[0][1])
        
        metadata = json.loads(media[0][1] or "{}")

        if "size" not in metadata and "size" in require_fields:
            metadata["size"] = int((await self.requester.head(media[0][0], headers={
                "Referer": media[0][0],
                "Cookie": "cda.player=html5",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3",
                "Range": "bytes=0-"
            }))['headers']['Content-Length'])

        self.series.service._database.update("media", ["metadata"], [json.dumps(metadata)], "media_id = ?", [media_id])
        
        return metadata

    async def get_sources(self, scrape: bool = True, force_scrape: Union[bool, List[str], str] = False, scrape_one: bool = False, update_db: bool = True, min_quality: int = 1080) -> List[dict]:
        if not isinstance(force_scrape, bool) and not isinstance(force_scrape, str) and not isinstance(force_scrape, list):
            raise ValueError("force_scrape must be a boolean, string or list of strings!")
        
        if isinstance(force_scrape, str):
            force_scrape = [force_scrape]
        
        if isinstance(force_scrape, list):
            for index, source in enumerate(force_scrape):
                if source.startswith("oa-"):
                    force_scrape[index] = source.removeprefix("oa-")
                
        
        if not force_scrape and self.sources:
            return self.sources

        data = "id=" + self.id
        player_list = json.loads(json.loads((await self.requester.post(self.series.service.player_list_url, headers={
            "Referer": self.series.url,
            "Content-Length": str(len(data.encode())),
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"
        }, data=data))['text'])['data'])

        players: List[OA_Source] = []
        tasks: List[Task] = []

        for player in player_list['players']:
            async def request_data(player, source: OA_Source):
                data = f"id={player['id']}"
                player_data = json.loads((await self.requester.post(self.series.service.player_data_url, headers={
                    "Referer": self.series.url,
                    "Content-Length": str(len(data.encode())),
                    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"
                }, data=data))['text'])

                if player['url'] == "cda":
                    cda_data = await CDA.source_extractor(player_data['data'], prefer_quality=player['quality'])
                    quality = source.quality if source.quality in list(cda_data.keys()) else str(max([int(key.removeSuffix("p")) for key in cda_data if key not in ["qualities", "duration"]])) + "p"
                    players[players.index(source)].url = cda_data[quality]
                    for quality in cda_data['qualities']:
                        if not quality in self.qualities:
                            self.qualities.append(quality)
 
                players[players.index(source)].prefetch_url = player_data['data']

            source = OA_Source(
                uid=f"oa-{player['id']}",
                id=player['id'],
                url=None,
                prefetch_url=None,
                audio_lang=player['audio'],
                sub_lang=player['sub'],
                source=player['url'],
                quality=player['quality'] or "unknown",
                subber=player['sub_group'] or "unknown"
            )

            if (source.source.lower() != "cda"):
                continue # TODO: Missing other scrappers for now!

            if (player.get('quality') or "unknown") not in self.qualities:
                self.qualities.append((player.get('quality') or "unknown"))

            if (source.id not in (force_scrape or []) and force_scrape != True) and \
             (any([normalize(sanitize(player.get('quality', 'unknown') or "unknown")) == normalize(sanitize(other_player.quality)) \
             and normalize(sanitize((player.get('sub_group', 'unknown') or "unknown").replace(" ", ""))) == normalize(sanitize(other_player.subber.replace(" ", ""))) for other_player in players]) \
             or (min_quality and int(player.get('quality', '-1p').replace('p', '') or 0) < min_quality)):
                players.append(source)
                continue
            
            players.append(source)
            
            if scrape:
                tasks.append(asyncio.create_task(request_data(player, source)))

            if scrape_one:
                break

        if tasks:
            await asyncio.wait(tasks, return_when=asyncio.ALL_COMPLETED)

        self.sources = players

        if update_db:
            for source in self.sources:
                self.sources[self.sources.index(source)].url = self.series.service.store_media(source.url, self, "episode", media_id=f"{source.id}", lookup_meta={
                    "subber": source.subber,
                    "quality": source.quality,
                    "audio_lang": source.audio_lang,
                    "sub_lang": source.sub_lang,
                    "source": source.source,
                }, uid=source.uid)

            in_db = bool(self.series.service._database.select("content", ["uid"], "uid = ?", [self.uid]))
            content_info = self.info("JSON")
            (self.series.service._database.update if in_db else
            self.series.service._database.insert)("content", [
                "uid",
                "origin_url",
                "searchable",
                "source",
                "weight",
                "type",
                "title",
                "meta"
            ], [
                self.uid,
                self.url,
                True,
                "ogladajanime",
                .6,
                "episode",
                self.title,
                json.dumps({key:content_info[key] for key in content_info if key not in ["uid", "title", "url"]})
            ], **({
                "where": "uid = ?",
                "where_values": [self.uid]
            } if in_db else {}))

        return players
    
    async def download(self, media_id: str, start: int, end: int, requester: Requester) -> bytes:
        media = self.series.service._database.select("media", ["origin_url", "metadata"], "id = ?", [media_id])

        if not media:
            raise ValueError("Media not found in database!")

        return (await requester.get(media[0][0], headers={
            "Referer": media[0][0],
            "Range": f"bytes={start}-{end}",
            "Cookie": "cda.player=html5",
        }))['data']

    def info(self, type: Literal['printable'] | Literal['JSON'] = "JSON", *args, **kwargs) -> dict:
        if type.lower() == "json":
            return {
                #**super().info("JSON"),
                "id": self.id,
                "uid": self.uid,
                "url": self.url,
                "title": self.title,
                "index": self.index,
                "lang": self.lang,
                "duration": self.duration,
                "series": self.series.uid,
                "sources": [source.info("JSON") for source in self.sources],
                "qualities": self.qualities
            }
        
        return super().info("printable") +\
            f"ID: {self.id}\n" +\
            f"UID: {self.uid}\n" +\
            f"URL: {self.url}\n" +\
            f"Title: {self.title}\n" +\
            f"Index: {self.index}\n" +\
            f"Language: {self.lang}\n" +\
            f"Duration (seconds): {self.duration}" +\
            f"Series: {self.series.uid}" +\
            f"Players: {self.players}" +\
            f"Qualities: {', '.join(self.qualities)}"

class OgladajAnime_pl(Service):
    def __init__(self, *args, database: Database, search_suggestion_cache_size: int = (1024 * 1024 * 100), **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self.codenames = ["ogladajanime", "oa"]
        self._database: Database = database

        self.base_url: str = "https://ogladajanime.pl"
        self.homepage_url: str = self.base_url
        self.search_suggestions_url: str = self.base_url + "/manager.php?action=get_anime_names"
        self.anime_url: str = self.base_url + "/manager.php?action=anime"
        self.player_list_url: str = self.base_url + "/manager.php?action=get_player_list"
        self.player_data_url: str = self.base_url + "/manager.php?action=change_player_url"

        self.logo_url: str = "/media/ogladajanime-logo-full.png"
        self.icon_url: str = "/media/ogladajanime-icon.png"

        self.search_suggestions: List[str] = []
        self.search_suggestions_cache: dict[str, list[str]] = {}
        self.search_suggestion_cache_size: int = search_suggestion_cache_size

        self.default_headers: dict = {
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Referer": self.base_url,
            "Host": self.base_url.split("://")[1].split("/")[0],
            "Origin": self.base_url,          
            "X-Requested-With": "XMLHttpRequest",
        }

    def store_media(self, url: str, owner: Union[OA_Episode, OA_Movie, OA_Series], media_name: Union[Literal["thumbnail"]], *, media_id: str = None, lookup_meta: Union[str, dict] = None, download_priority: int = 0, uid: str = None):
        existing = self._database.select("media", ["id", "origin_url", "refers_to"], "origin_url = ? AND refer_id != ?", [url, owner.uid])
        existing_exact = self._database.select("media", ["id", "origin_url", "refers_to", "metadata"], "uid = ?", [uid]) or \
        self._database.select("media", ["id", "origin_url", "refers_to", "metadata"], "origin_url = ? AND refer_id = ?", [url, owner.uid])
        if media_name == "thumbnail":
            format = (url or "").split("?")[0].split(".")[-1]
            media_id = f"{int(url.split('?')[0].split('/')[-1].split('.')[0].replace('w', ''))}w"
            media_type = "image"

        if media_name == "episode":
            format = (url or "").split("?")[0].split(".")[-1] or "UNKNOWN"
            media_type = "video"



        if not lookup_meta:
            lookup_meta = {}

        if isinstance(lookup_meta, dict):
            lookup_meta = json.dumps(lookup_meta)



        if any([not x for x in [format, media_id, media_type]]):
            raise ValueError("Missing media metadata!")

        if existing_exact:
            metadata = json.loads(existing_exact[0][3])
            self._database.update("media",
            [
                "uid",
                "refer_id",
                "download_priority",
                "metadata",
                "media_type",
                "media_format",
                "media_name",
                "media_id",
                "origin_url",
                "data_path",
                "refers_to"
            ], [
                uid,
                owner.uid,
                download_priority or 0,
                json.dumps({**metadata, **json.loads(lookup_meta)}),
                media_type,
                format,
                media_name,
                media_id,
                url,
                None,
                None
            ], "uid = ?", [uid])
        elif existing:
            refers_to = existing[0][2] or existing[0][0]
            self._database.insert("media", [
                    "uid",
                    "refer_id",
                    "download_priority",
                    "metadata",
                    "media_type",
                    "media_format",
                    "media_name",
                    "media_id",
                    "origin_url",
                    "data_path",
                    "refers_to"
                ], [
                    uid,
                    owner.uid,
                    download_priority or 0,
                    lookup_meta,
                    media_type,
                    format,
                    media_name,
                    media_id,
                    None,
                    None,
                    refers_to
                ]
            )
            
        else:
            self._database.insert("media", [
                    "uid",
                    "refer_id",
                    "download_priority",
                    "metadata",
                    "media_type",
                    "media_format",
                    "media_name",
                    "media_id",
                    "origin_url",
                    "data_path",
                    "refers_to"
                ], [
                    uid,
                    owner.uid,
                    download_priority or 0,
                    lookup_meta,
                    media_type,
                    format,
                    media_name,
                    media_id,
                    url,
                    None,
                    None
                ]
            )

        return f"/cdn/media/{owner.uid}/{media_name}?format={format}&id={media_id}"

    def get_by_uid(self, uid: str, get_similar: bool = False, get_episodes: bool = False) -> Union[OA_Movie, OA_Series, OA_Episode]:
        if not uid.startswith("oa-"):
            raise ValueError("Invalid UID")

        content = self._database.select("content", ["origin_url", "type", "title", "meta"], "uid = ?", [uid])
        if not content:
            raise ValueError("Content not found")
        
        content = content[0]
        if content[1] == "movie":
            movie_data: dict = json.loads(content[3])
            movie = OA_Movie(
                url=content[0],
                uid=uid,
                service=self,
                title=content[2],
                requester=self.requester,
                **{key: movie_data[key] for key in movie_data if key not in ["service"]}
            )
        
            movie.similar = [self.get_by_uid(similar, False, True) for similar in movie_data["similar"]] if get_similar else []
            return movie

        if content[1] == "episode":
            episode_data = json.loads(content[3])

            return OA_Episode(
                url=content[0],
                uid=uid,
                service=self,
                series=self.get_by_uid(episode_data.pop("series"), False, False),
                title=content[2],
                requester=self.requester,
                **episode_data
            )
        
        series_data: dict = json.loads(content[3])
        series = OA_Series(
            url=content[0],
            uid=uid,
            service=self,
            title=content[2],
            requester=self.requester,
            **{key: series_data[key] for key in series_data if key not in ["service"]}
        )
        series.episodes = [self.get_by_uid(episode, False, False) for episode in series_data["episodes"]] if get_episodes else []
        series.similar = [self.get_by_uid(similar, False, True) for similar in series_data["similar"]] if get_similar else []
        
        return series

    async def get_search_suggestions(self, query: str, limit: int, *, force_get: bool = False) -> list[str]:
        if force_get or not self.search_suggestions:
            self.search_suggestions = json.loads((await self.requester.get(self.search_suggestions_url))['text'])['json']

        if query in self.search_suggestions_cache and len(self.search_suggestions_cache[query]) >= limit:
            return self.search_suggestions_cache[query][:limit]
        
        suggestions = self.search_suggestions_cache.get(query[:-1], None) or self.search_suggestions
        if len(suggestions) < limit:
            suggestions = self.search_suggestions

        to_return = []

        for suggestion in suggestions:
            if suggestion.lower().replace(" ", "").startswith(query.lower().replace(" ", "")):
                to_return.append(suggestion)
            
                if len(to_return) >= limit:
                    break

        if len(to_return) < limit and len(suggestions) < len(self.search_suggestions):
            for suggestion in self.search_suggestions:
                if suggestion.lower().replace(" ", "").startswith(query.lower().replace(" ", "")):
                    to_return.append(suggestion)
                
                    if len(to_return) >= limit:
                        break

        self.search_suggestions_cache[query] = to_return

        return to_return

    async def search(self, query: str, scrape: bool = False, force_scrape: bool = False) -> list[Union[OA_Movie, OA_Series]]:
        def scrape_children(children: bs4.element.Tag) -> Union[OA_Movie, OA_Series]:    
            media_type = normalize(sanitize(children.find("span", class_="badge").text))
            content = (OA_Movie if media_type == "movie" else OA_Series)(
                id=sanitize(children.find("h5").find("a")["title"]),
                uid=f"oa-{sanitize(children.find('h5').find('a')['title'])}",
                service=self,
                url=self.base_url + sanitize(children.find("h5").find("a")["href"]),
                title=sanitize(children.find("h5").find("a").text),
                thumbnail=sanitize(children.find("img")["data-srcset"].split(" ")[0]),
                description=sanitize(children.find("p").text),
                **({
                    "series_type": sanitize(children.find("span", class_="badge").text)
                } if normalize(sanitize(children.find("span", class_="badge").text)) != "movie" else {})
            )

            content.thumbnail = self.store_media(sanitize(children.find("img")["data-srcset"].split(" ")[0]), content, "thumbnail", download_priority=1)

            if not self._database.select("content", ["uid"], "uid = ?", [content.uid]):
                content_info = content.info("JSON")
                self._database.insert("content", [
                    "uid",
                    "origin_url",
                    "searchable",
                    "source",
                    "weight",
                    "type",
                    "title",
                    "meta"
                ], [
                    content.uid,
                    content.url,
                    True,
                    "ogladajanime",
                    1,
                    media_type,
                    content.title,
                    json.dumps({key:content_info[key] for key in content_info if key not in ["uid", "title", "url"]})
                ])

            return content
        
        data = f"search={query}&search_type=name"

        headers = self.default_headers.copy()
        headers = {
            **headers,
            "Referer": self.base_url + "/search/name/" + query.replace(" ", "-"),
            "Origin": self.base_url,
            "Content-Length": str(len(data.encode()))
        }

        response = await self.requester.post(self.base_url + "/search/name/" + query.replace(" ", "-"), headers=headers, data=data)
        if response['status'] != 200:
            raise ConnectionError("Failed to connect to the server")
        
        soup = bs4.BeautifulSoup(response['text'], "html.parser")

        results: List[Union[OA_Movie, OA_Series]] = []

        for children in soup.find(id="anime_main").find_all("div", recursive=False):           
           result = scrape_children(children)           
           results.append(result)

        if scrape:
            await asyncio.gather(*[media.scrape(False) for media in results if not force_scrape and not self._database.select("content", ["uid"], "uid = ?", [media.uid])])

        return results

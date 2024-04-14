import asyncio, json, bs4
from asyncio import Task
from typing import Optional, List, Tuple, Union, Literal
from datetime import datetime
from urllib.parse import quote as urlquote, unquote as urlunquote
from scripts.helper.requester import Requester
from scripts.helper.database import Database
from scripts.helper.util import sanitize, normalize

class Service:
    def __init__(self, *args, requester: Requester = None, **kwargs) -> None:
        self.base_url: str = None
        self.homepage_url: str = None
        self.search_suggestions_url: str = None

        self.default_headers: dict = {}

        self.requester: Requester = requester or Requester(default_headers={
            "Referer": self.base_url,
            "X-Requested-With": "XMLHttpRequest"
        }, max_requests_per_minute=20, max_requests_per_second=20)

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
            }

        return f"Base URL: {self.base_url}\n" +\
         f"Homepage URL: {self.homepage_url}\n" +\
         f"Search Suggestions URL: {self.search_suggestions_url}"

class Movie:
    def __init__(self, url: str, uid: str, title: str = None, thumbnail: str = None, description: str = None,
     genres: List[str] = None, release_year: int = None, duration: str = None, rating: float = None,
     director: str = None, actors: List[str] = None, trailer_url: str = None, similar: List["Movie"] = None, *args, requester: Requester = None, **kwargs) -> None:
        self.url: str = url
        self.uid: str = uid
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
                "thumbnail": self.thumbnail,
                "description": self.description,
                "genres": self.genres,
                "release_year": self.release_year,
                "duration": self.duration,
                "rating": self.rating,
                "director": self.director,
                "similar": [similar.url for similar in self.similar]
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
    def __init__(self, url: str, uid: str, title: str = None, thumbnail: str = None, description: str = None,
     genres: List[str] = None, release_time: Tuple[Union[datetime, int], Union[datetime, int]] = None,
     episodes: Union[dict[str, List["Episode"]], List["Episode"]] = None, 
     similar: List[Union["Series", "Movie"]] = None, *args, requester: Requester = None, **kwargs) -> None:
        
        self.url: str = url
        self.uid: str = uid
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
                "description": self.description,
                "genres": self.genres,
                "release_time": [int(self.release_time[0].timestamp()), (int(self.release_time[1].timestamp()) if self.release_time[1] else None)] if self.release_time else None,
                "episodes": [episode.uid for episode in self.episodes] if not get_full_episodes else [episode.info() for episode in self.episodes],
                "similar": [similar.uid for similar in self.similar] if not get_full_similar else [similar.info("JSON", False, False) for similar in self.similar]
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
    def __init__(self, url: str, uid: str, title: str = None, thumbnail: str = None, release_date: datetime = None,
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

class OA_Movie(Movie):
    def __init__(self, url: str, uid: str, service: "OgladajAnime_pl", id: int = None, pegi: str = None, alternate_titles: List[str] = None,
         tags: List['str'] = None, views: int = None, rating: float = None, length: int = None,
         trailer_url: str = None, *args, **kwargs) -> None:
        super().__init__(url, uid, *args, **kwargs)

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

    def info(self, type: Union[Literal['printable'], Literal['JSON']] = "JSON") -> dict:
        if type.lower() == "json":
            return {
                **super().info("JSON"),
                "id": self.id,
                "type": "movie",
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
        super().__init__(url, uid, *args, **kwargs)

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

    async def scrape(self, scrape_similar: bool = True) -> None:
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
            srating, spegi, stype = [element.text for element in similar.find_all("span")]
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
            episodes.append(OA_Episode(
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

    def info(self, type: Union[Literal['printable'], Literal['JSON']] = "JSON", get_full_similar: bool = False, get_full_episodes: bool = False) -> dict:
        if type.lower() == "json":
            return {
                **super().info("JSON", get_full_similar, get_full_episodes),
                "id": self.id,
                "series_type": self.series_type,
                "type": "series",
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
    
class OA_Episode(Episode):
    def __init__(self, url: str, uid: str, index: int, service: "OgladajAnime_pl", series: OA_Series, title: str, lang: str,
        duration: str = None,*args, requester: Requester, **kwargs) -> None:
        super().__init__(url, uid, title, None, None, duration, None, *args, requester=requester, **kwargs)

        self.index: int = index
        self.service: "OgladajAnime_pl" = service
        self.series: OA_Series = series
        self.lang: str = lang

    def info(self, type: Literal['printable'] | Literal['JSON'] = "JSON") -> dict:
        if type.lower() == "json":
            return {
                "uid": self.uid,
                "url": self.url,
                "title": self.title,
                "index": self.index,
                "lang": self.lang,
                "duration": self.duration,
                "series": self.series.uid
            }
        
        return f"UID: {self.uid}\n" +\
            f"URL: {self.url}\n" +\
            f"Title: {self.title}\n" +\
            f"Index: {self.index}\n" +\
            f"Language: {self.lang}\n" +\
            f"Duration (seconds): {self.duration}" +\
            f"Series: {self.series.uid}"

class OgladajAnime_pl(Service):
    def __init__(self, *args, database: Database, search_suggestion_cache_size: int = (1024 * 1024 * 100), **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self._database: Database = database

        self.base_url: str = "https://ogladajanime.pl"
        self.search_suggestions_url: str = "https://ogladajanime.pl/manager.php?action=get_anime_names"
        self.anime_url: str = "https://ogladajanime.pl/manager.php?action=anime"

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

    def get_by_uid(self, uid: str, get_similar: bool = False, get_episodes: bool = False, series: OA_Series = None) -> Union[OA_Movie, OA_Series, OA_Episode]:
        if not uid.startswith("oa-"):
            raise ValueError("Invalid UID")

        content = self._database.select("content", ["origin_url", "type", "title", "meta"], "uid = ?", [uid])
        if not content:
            raise ValueError("Content not found")
        
        content = content[0]
        if content[1] == "movie":
            return OA_Movie(
                url=content[0],
                uid=uid,
                service=self,
                title=content[2],
                requester=self.requester,
                **json.loads(content[3])
            )

        if content[1] == "episode":
            if not series:
                raise ValueError("Series not provided for episode!")

            return OA_Episode(
                url=content[0],
                uid=uid,
                service=self,
                series=series,
                title=content[2],
                requester=self.requester,
                **{key: value for key, value in json.loads(content[3]).items() if key not in ["series"]}
            )
        
        series_data: dict = json.loads(content[3])
        series = OA_Series(
            url=content[0],
            uid=uid,
            service=self,
            title=content[2],
            requester=self.requester,
            **series_data
        )
        series.episodes = [self.get_by_uid(episode, False, False, series) for episode in series_data["episodes"]] if get_episodes else []
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

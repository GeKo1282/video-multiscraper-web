import asyncio, json, bs4
from typing import Optional, List, Tuple, Union, Literal
from datetime import datetime
from urllib.parse import quote as urlquote, unquote as urlunquote
from scripts.helper.requester import Requester

class Service:
    def __init__(self, *, requester: Requester = None) -> None:
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

    async def get_homepage_suggestions(self, *, user_agent: Optional[str] = None, headers: Optional[dict] = None) -> List[str]:
        '''
            This method is intended to be overwritten by devired classes.
        '''

    async def search(self, query: str, *, user_agent: Optional[str] = None, headers: Optional[dict] = None) -> List[Union["Movie", "Series"]]:
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
    def __init__(self, url: str, title: str = None, thumbnail: str = None, description: str = None,
     genres: List[str] = None, release_year: int = None, duration: str = None, rating: float = None,
     director: str = None, actors: List[str] = None, trailer_url: str = None, similar: List["Movie"] = None, *, requester: Requester = None) -> None:
        self.url: str = url
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

    async def scrap(self, *, user_agent: Optional[str] = None, headers: Optional[dict] = None) -> None:
        '''
            This method is intended to be overwritten by devired classes.
        '''

    async def get_sources(self, *, user_agent: Optional[str] = None, headers: Optional[dict] = None) -> List[str]:
        '''
            This method is intended to be overwritten by devired classes.
        '''

    def info(self, type: Union[Literal['printable'], Literal['JSON']] = "JSON") -> dict:
        if type.lower() == "json":
            return {
                "url": self.url,
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
    def __init__(self, url: str, title: str = None, thumbnail: str = None, description: str = None,
     genres: List[str] = None, release_time: Tuple[datetime, datetime] = None,
     episodes: Union[dict[str, List["Episode"]], List["Episode"]] = None, 
     similar: List[Union["Series", "Movie"]] = None, *, requester: Requester = None) -> None:
        self.url: str = url
        self.is_scrapped: bool = False if not all([
            title, thumbnail, description, genres, release_time, episodes
        ]) else True

        self.title: str = title
        self.thumbnail: str = thumbnail
        self.description: str = description
        self.genres: List[str] = genres or []
        self.release_time: Tuple[datetime, Optional[datetime]] = release_time

        self.episodes: Union[dict[str, List[Episode]], List[Episode]] = episodes or []

        self.similar: List[Union[Series, Movie]] = similar or []
        
        self.requester: Requester = requester or Requester(default_headers={
            "Referer": self.url.split("://")[0] + "://" + self.url.split("://")[1].split("/")[0] + "/",
            "X-Requested-With": "XMLHttpRequest"
        }, max_requests_per_minute=20, max_requests_per_second=20)

    async def scrap(self, *, user_agent: Optional[str] = None, headers: Optional[dict] = None) -> None:
        '''
            This method is intended to be overwritten by devired classes.
        '''

    async def get_sources(self, *, user_agent: Optional[str] = None, headers: Optional[dict] = None) -> List[str]:
        '''
            This method is intended to be overwritten by devired classes.
        '''

    def info(self, type: Union[Literal['printable'], Literal['JSON']] = "JSON") -> dict:
        if type.lower() == "json":
            return {
                "url": self.url,
                "title": self.title,
                "thumbnail": self.thumbnail,
                "description": self.description,
                "genres": self.genres,
                "release_time": [int(self.release_time[0].timestamp()), (int(self.release_time[1].timestamp()) if self.release_time[1] else None)] if self.release_time else None,
                "episodes": [episode.info() for episode in self.episodes],
                "similar": [similar.url for similar in self.similar]
            }
        
        return f"URL: {self.url}\n" +\
            f"Title: {self.title}\n" +\
            f"Thumbnail: {self.thumbnail}\n" +\
            f"Description: {self.description}\n" +\
            f"Genres: {', '.join(self.genres)}\n" +\
            f"Release Time: {self.release_time[0].strftime('%Y-%m-%d %H:%M:%S')} - {self.release_time[1].strftime('%Y-%m-%d %H:%M:%S')}\n" +\
            f"Episodes: {', '.join([episode.title for episode in self.episodes])}"

class Episode:
    def __init__(self, url: str, title: str = None, thumbnail: str = None, release_date: datetime = None,
        duration: str = None, description: str = None, *, requester: Requester = None) -> None:
        self.url: str = url
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
        
    async def scrap(self, *, user_agent: Optional[str] = None, headers: Optional[dict] = None) -> None:
        '''
            This method is intended to be overwritten by devired classes.
        '''

    async def get_sources(self, *, user_agent: Optional[str] = None, headers: Optional[dict] = None) -> List[str]:
        '''
            This method is intended to be overwritten by devired classes.
        '''

    def info(self, type: Union[Literal['printable'], Literal['JSON']] = "JSON") -> dict:
        if type.lower() == "json":        
            return {
                "url": self.url,
                "title": self.title,
                "thumbnail": self.thumbnail,
                "release_date": self.release_date.timestamp(),
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
    def __init__(self, url: str, id: int = None, pegi: str = None, alternate_titles: List[str] = None,
         tags: List['str'] = None, views: int = None, rating: float = None, length: int = None,
         trailer_url: str = None, *args, **kwargs) -> None:
        super().__init__(url, *args, **kwargs)

        self.id: int = id
        self.pegi: str = pegi
        self.alternate_titles: List[str] = alternate_titles or []
        self.tags: List[str] = tags or []
        self.views: int = views
        self.rating: float = rating
        self.length: int = length
        self.trailer_url: str = trailer_url

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
    def __init__(self, url: str, id: int = None, series_type: str = None, pegi: str = None, alternate_titles: List[str] = None,
         tags: List['str'] = None, views: int = None, rating: float = None, episode_count: int = None, episode_length: int = None,
         trailer_url: str = None, status: str = None, *args, **kwargs) -> None:
        super().__init__(url, *args, **kwargs)

        if any([not id, not series_type, not pegi, not views, not rating]):
            self.is_scrapped = False

        self.id: int = id
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

    def info(self, type: Union[Literal['printable'], Literal['JSON']] = "JSON") -> dict:
        if type.lower() == "json":
            return {
                **super().info("JSON"),
                "id": self.id,
                "series_type": self.series_type,
                "type": "series",
                "pegi": self.pegi,
                "alternate_titles": self.alternate_titles,
                "tags": self.tags,
                "views": self.views,
                "rating": self.rating,
                "episodes": self.episodes,
                "episode_length": self.episode_length,
                "trailer_url": self.trailer_url,
                "status": self.status
            }
        
        return super().info("printable") + f"ID: {self.id}\n" +\
         f"Type: {self.type}"
    
class OA_Episode(Episode):
    pass

class OgladajAnime_pl(Service):
    def __init__(self, *args, search_suggestion_cache_size: int = (1024 * 1024 * 100), **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self.base_url: str = "https://ogladajanime.pl"
        self.search_suggestions_url: str = "https://ogladajanime.pl/manager.php?action=get_anime_names"

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

    async def search(self, query: str, get_tooltips: bool = True, timeout: int = 10) -> list[Union[OA_Movie, OA_Series]]:
        async def scrape_children(children: bs4.element.Tag, get_tooltips: bool = True) -> Union[OA_Movie, OA_Series]:
            if "h5" not in str(children):
                return None
            
            if get_tooltips:
                tooltip_request_data = f"id={sanitize(children.find('h5').find('a')['title'])}"
                try:
                    tooltip = bs4.BeautifulSoup(json.loads((await self.requester.post(
                        self.base_url + "/manager.php?action=get_anime_tooltip",
                        data=tooltip_request_data,
                        headers = {
                            **headers,
                            "Content-Length": str(len(tooltip_request_data.encode())),
                            "Referer": self.base_url + "/search/name/" + query.replace(" ", "-"),
                        },
                        timeout=timeout
                    ))['text'])['data'], "html.parser")
                except:
                    pass

                media_type, pegi, rating, views, episodes_and_time, comments = [
                    element.text for element in tooltip.find("div", class_="card-body").findChildren("div", recursive=False)[-1].find_all("span")
                ]
                episode_count, time_of_episode = episodes_and_time.strip().split(" ")
                status, *emission = [
                    element.find("div").text for element in tooltip.find("div", class_="card-body").findChildren("div", recursive=False)[-3].find_all("small")
                ]

                media_type = normalize(sanitize(media_type))

                if media_type == "movie":
                    emission_start = emission_end = emission
                elif type(emission) == list and len(emission) > 1 and emission[1]:
                    emission_start, emission_end = emission[0], emission[1]
                else:
                    emission_start = emission[0]
                    emission_end = None

                return (OA_Movie if media_type == "movie" else OA_Series)(
                    id=sanitize(children.find("h5").find("a")["title"]),
                    url=self.base_url + sanitize(children.find("h5").find("a")["href"]),
                    title=sanitize(children.find("h5").find("a").text),
                    thumbnail=sanitize(children.find("img")["data-srcset"].split(" ")[0]),
                    description=sanitize(children.find("p").text),
                    pegi=sanitize(pegi),
                    alternate_titles=[sanitize(title) for title in tooltip.find("small", class_="text-trim").text.split("|")],
                    views=int(views.replace(" ", "")),
                    trailer_url=sanitize(tooltip.find("iframe")["src"]) if tooltip.find("iframe") else None,
                    genres=[sanitize(element.text) for element in tooltip.find("div", class_="card-body").findChildren("div", recursive=False)[-5].find_all("span")],
                    tags=[sanitize(element.text) for element in tooltip.find("div", class_="card-body").findChildren("div", recursive=False)[-4].find_all("span")],
                    rating=float(sanitize(rating)),
                    **({
                        "series_type": sanitize(children.find("span", class_="badge").text),
                        "release_time": (datetime.strptime(emission_start, "%Y-%m-%d"), (datetime.strptime(emission_end, "%Y-%m-%d") if status == "Zakończone" and emission_end else None)),
                        "episode_count": int(episode_count),
                        "episode_length": int(sanitize(time_of_episode)[1:-1].replace("min", "")) * 60,
                        "status": sanitize(status)
                    } if normalize(sanitize(children.find("span", class_="badge").text)) != "movie" else {
                        "length": int(sanitize(time_of_episode)[1:-1].replace("min", "")) * 60
                    })
                )

            return (OA_Movie if normalize(sanitize(children.find("span", class_="badge").text)) == "movie" else OA_Series)(
                id=sanitize(children.find("h5").find("a")["title"]),
                url=self.base_url + sanitize(children.find("h5").find("a")["href"]),
                title=sanitize(children.find("h5").find("a").text),
                thumbnail=sanitize(children.find("img")["data-srcset"].split(" ")[0]),
                description=sanitize(children.find("p").text),
                **({
                    "series_type": sanitize(children.find("span", class_="badge").text)
                } if normalize(sanitize(children.find("span", class_="badge").text)) != "movie" else {})
            )

        def sanitize(string: str) -> str:
            return string.replace("\t", "").strip("\n")
        
        def normalize(string: str):
            return string.replace(" ", "-").lower()
        
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

        scrappers = []

        for children in soup.find(id="anime_main").children:
           scrappers.append(scrape_children(children, get_tooltips))

        results = await asyncio.gather(*scrappers)

        results = [result for result in results if result]

        return results

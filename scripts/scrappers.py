import requests, json, bs4
from typing import Optional, List, Tuple, Union, Literal
from datetime import datetime
from urllib.parse import quote as urlquote, unquote as urlunquote

class Service:
    def __init__(self, *, default_agent: Optional[str] = None) -> None:
        self.base_url: str = None
        self.homepage_url: str = None
        self.search_suggestions_url: str = None

        self.default_headers: dict = {}
        self.default_agent: Optional[str] = default_agent

    def get_search_suggestions(self, hint: str = None, limit: int = 10, *, user_agent: Optional[str] = None, headers: Optional[dict] = None) -> List[str]:
        '''
            This method is intended to be overwritten by devired classes.
        '''

    def get_homepage_suggestions(self, *, user_agent: Optional[str] = None, headers: Optional[dict] = None) -> List[str]:
        '''
            This method is intended to be overwritten by devired classes.
        '''

    def search(self, query: str, *, user_agent: Optional[str] = None, headers: Optional[dict] = None) -> List[Union["Movie", "Series"]]:
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
     director: str = None, actors: List[str] = None, trailer_url: str = None, similar: List["Movie"] = None) -> None:
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
        self.actors: List[str] = actors or []

        self.similar: List[Movie] = similar or []

    def scrap(self, *, user_agent: Optional[str] = None, headers: Optional[dict] = None) -> None:
        '''
            This method is intended to be overwritten by devired classes.
        '''

    def get_sources(self, *, user_agent: Optional[str] = None, headers: Optional[dict] = None) -> List[str]:
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
                "actors": self.actors,
                "similar": [movie.url for movie in self.similar]
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
     episodes: Union[dict[str, List["Episode"]], List["Episode"]] = None) -> None:
        self.url: str = url
        self.is_scrapped: bool = False if not all([
            title, thumbnail, description, genres, release_time, episodes
        ]) else True

        self.title: str = title
        self.thumbnail: str = thumbnail
        self.description: str = description
        self.genres: List[str] = genres or []
        self.release_time: Tuple[datetime, datetime] = release_time

        self.episodes: Union[dict[str, List[Episode]], List[Episode]] = episodes or []


    def scrap(self, *, user_agent: Optional[str] = None, headers: Optional[dict] = None) -> None:
        '''
            This method is intended to be overwritten by devired classes.
        '''

    def get_sources(self, *, user_agent: Optional[str] = None, headers: Optional[dict] = None) -> List[str]:
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
                "release_time": [self.release_time[0].timestamp(), self.release_time[1].timestamp()] if self.release_time else None,
                "episodes": [episode.info() for episode in self.episodes]
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
        duration: str = None, description: str = None) -> None:
        self.url: str = url
        self.is_scrapped: bool = False if not all([
            title, thumbnail, release_date, duration, description
        ]) else True

        self.title: str = title
        self.thumbnail: str = thumbnail
        self.release_date: datetime = release_date
        self.duration: str = duration
        self.description: str = description
        
    def scrap(self, *, user_agent: Optional[str] = None, headers: Optional[dict] = None) -> None:
        '''
            This method is intended to be overwritten by devired classes.
        '''

    def get_sources(self, *, user_agent: Optional[str] = None, headers: Optional[dict] = None) -> List[str]:
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
    def __init__(self, url: str, id: int = None, *args, **kwargs) -> None:
        super().__init__(url, *args, **kwargs)

        self.id: int = id

class OA_Series(Series):
    def __init__(self, url: str, id: int = None, type: str = None, *args, **kwargs) -> None:
        super().__init__(url, *args, **kwargs)

        self.id: int = id
        self.type: str = type

class OA_Episode(Episode):
    pass

class OgladajAnime_pl(Service):
    def __init__(self, default_agent: Optional[str]) -> None:
        super().__init__(default_agent=default_agent)

        self.base_url: str = "https://ogladajanime.pl"
        self.search_suggestions_url: str = "https://ogladajanime.pl/manager.php?action=get_anime_names"

        self.default_headers: dict = {
            "Referer": self.base_url,
            "X-Requested-With": "XMLHttpRequest"
        }
        self.default_agent: Optional[str] = default_agent

    def get_search_suggestions(self, user_agent: Optional[str] = None) -> list[str]:
        agent = user_agent or self.default_agent or None
        if not agent:
            raise ValueError("No user agent provided")
        
        headers = self.default_headers.copy()
        headers["User-Agent"] = agent

        return json.loads(requests.get(self.search_suggestions_url, headers=headers).text)['json']
    
    def search(self, query: str, user_agent: Optional[str] = None) -> list[Union[Movie, Series]]:
        def sanitize(string: str) -> str:
            return string.replace("\t", "").strip("\n")
        
        def normalize(string: str):
            return string.replace(" ", "-").lower()

        agent = user_agent or self.default_agent or None
        if not agent:
            raise ValueError("No user agent provided")
        
        data = urlquote(f"search={query}&search_type=name")

        headers = self.default_headers.copy()
        headers = {
            **headers,
            "Referer": self.base_url + "/search/name/" + query.replace(" ", "-"),
            "User-Agent": agent,
            "Origin": self.base_url,
            "Content-Length": str(len(data.encode()))
        }

        response = requests.post(self.base_url + "/search/name/" + query.replace(" ", "-"), headers=headers, data=data)
        if response.status_code != 200:
            raise ConnectionError("Failed to connect to the server")
        
        soup = bs4.BeautifulSoup(response.text, "html.parser")

        results = []

        for children in soup.find(id="anime_main").children:
            if "h5" not in str(children):
                continue

            if normalize(sanitize(children.find("span", class_="badge").text)) == "movie":
                results.append(OA_Movie(
                    id=sanitize(children.find("h5").find("a")["title"]),
                    url=self.base_url + sanitize(children.find("h5").find("a")["href"]),
                    title=sanitize(children.find("h5").find("a").text),
                    thumbnail=sanitize(children.find("img")["data-srcset"].split(" ")[0]),
                    description=sanitize(children.find("p").text)
                ))
            else:
                results.append(OA_Series(
                    id=sanitize(children.find("h5").find("a")["title"]),
                    url=self.base_url + sanitize(children.find("h5").find("a")["href"]),
                    title=sanitize(children.find("h5").find("a").text),
                    thumbnail=sanitize(children.find("img")["data-srcset"].split(" ")[0]),
                    description=sanitize(children.find("p").text),
                    type=sanitize(children.find("span", class_="badge").text)
                ))

        return results

if __name__ == "__main__":
    scrapper = OgladajAnime_pl("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3")
    with open("search.json", "w") as file:
        file.write(json.dumps([x.info() for x in scrapper.search("My Hero Academia")], indent=4))
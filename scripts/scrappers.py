import requests, json
from typing import Optional

class Service:
    pass

class Movie:
    pass

class Series:
    pass

class Episode:
    pass

class OgladajAnime_pl:
    def __init__(self, default_agent: Optional[str]) -> None:
        self.search_suggestions_url: str = "https://ogladajanime.pl/manager.php?action=get_anime_names"

        self.default_headers: dict = {
            "Referer": "https://ogladajanime.pl/",
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
    
if __name__ == "__main__":
    scrapper = OgladajAnime_pl("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3")
    with open("suggestions.txt", "w") as file:
        file.write(json.dumps(scrapper.get_search_suggestions(), indent=4))
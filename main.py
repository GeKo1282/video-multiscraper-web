import json, os
from typing import List, Optional, AnyStr, Tuple, Any
from pathlib import Path
from scripts.webserver import WebServer
from scripts.api import Extender as APIExtender
from scripts.helper.logger import Fore, Color

class ProgramController:
    def __init__(self, prepare: bool = False):
        self.webserver: WebServer = WebServer()
        self.api_extender: APIExtender = None

        self.settings: dict = {}

        self.default_settings = {
            "webserver": {
                "host": "0.0.0.0",
                "port": 80
            },
            "socketserver": {
                "host": "0.0.0.0",
                "port": 5001
            }
        }

        if prepare:
            self.prepare()

    def prepare(self):
        self.settings = self.load_settings()
        print(self.settings)

        self.api_extender = APIExtender(socket_host=self.settings['socketserver']['host'], socket_port=self.settings['socketserver']['port'])

        self.webserver.add_path("/", ["POST"], self.api_extender)
        self.webserver.register_paths()

    def load_settings(self, settings_path: str = "data/settings.json") -> dict:
        # Loads, checks if valid and corrects settings if necessary
        def validator(settings: dict, parent_path: Optional[List[str]] = None, validate_to: dict = self.default_settings) -> dict:
            missing = []
            for key in validate_to.keys():
                if not key in settings.keys():
                    missing.append(((parent_path or []) + [key], validate_to[key]))
                    continue

                if type(validate_to[key]) == dict:
                    missing += validator(settings[key], (parent_path or []) + [key], validate_to[key])

            return missing or True
        
        def parser(path: List[str], defaults: AnyStr, color_dict: dict = None, splitter: AnyStr = "=>") -> str:
            if not color_dict:
                color_dict = {}
            outstr = ""

            for p in path:
                outstr += f"{color_dict.get('path_part', '')}{p}"

                if path.index(p) != len(path) - 1:
                    outstr += f" {color_dict.get('splitter', '')}{splitter} "
                else:
                    outstr += f": {color_dict.get('end', '')}{defaults}"

            outstr += Color.RESET
            return outstr
        
        def compliment(settings: dict, compliments: List[Tuple[List[str], Any]]):
            def update_nested_dict(d: dict, keys: List[str], value: Any):
                if len(keys) == 1:
                    d[keys[0]] = value
                else:
                    key = keys.pop(0)
                    if key in d:
                        update_nested_dict(d[key], keys, value)

            for compliment in compliments:
                update_nested_dict(settings, compliment[0], compliment[1])

        settings_path = Path(settings_path).absolute()

        if not settings_path.exists():
            os.makedirs(settings_path.parent, exist_ok=True)
            with open(settings_path, "w") as f:
                json.dump({}, f, indent=4)

        settings = json.load(open(settings_path))

        validated = validator(settings)
        if validated != True:
            print(f"Some settings are missing!")
            for index, missing in enumerate(validated):
                print(f"{index + 1}. {parser(missing[0], missing[1], color_dict={'path_part': Fore.YELLOW, 'splitter': Fore.CYAN, 'end': Fore.RED})}")
            print(f"Those defaults will be used during runtime. If you would like to change them, please edit the settings file at {Fore.YELLOW}{settings_path}{Color.RESET} and restart the program.")
            print(f"Would you like to save the defaults to the settings file? ([Y]es/[N]o): ", end="")
            while response := input().lower()[1:]:
                if response in ["y", "yes"]:
                    with open(settings_path, "w") as f:
                        json.dump(self.default_settings, f, indent=4)
                    print(f"Settings saved to {Fore.YELLOW}{settings_path}{Color.RESET}.")
                    break
                elif response in ["n", "no"]:
                    print(f"Settings not saved, but will be used during runtime.")
                    settings = compliment(settings, validated)
                    break
                else:
                    print(f"Invalid input. Please try again: ", end="")

        return settings

    def start(self):
        pass


def main():
    SETTINGS = json.load(open("data/settings.json"))

    webserver = WebServer()
    api_extender = APIExtender(socket_host=SETTINGS['socketserver']['host'], socket_port=SETTINGS['socketserver']['port'])
    webserver.add_path("/", ["POST"], api_extender)
    webserver.register_paths()
    webserver.run(SETTINGS['webserver']['host'], SETTINGS['webserver']['port'])

if __name__ == "__main__":
    ProgramController(prepare=True).start()
import json, os, base64, asyncio
from typing import List, Optional, AnyStr, Tuple, Any, Literal, Union, Callable, Dict
from pathlib import Path
from threading import Thread
from datetime import datetime
from scripts.webserver import WebExtender
from scripts.scrappers import OgladajAnime_pl
from scripts.api import APIExtender
from scripts.sockethandler import *
from scripts.helper.http import WebServer
from scripts.helper.socket import WebSocketServer, WebSocketClientProtocol, websockets, SocketSession
from scripts.helper.logger import Fore, Color
from scripts.helper.cipher import RSACipher, AESCipher
from scripts.helper.util import generate_id, sha512
from scripts.helper.database import Database
from scripts.helper.requester import Requester

class ProgramController:
    def __init__(self, prepare: bool = False):
        self.webserver: WebServer = WebServer()
        self.websocketserver: WebSocketServer = WebSocketServer()

        self.rsa: RSACipher = None

        self.settings: dict = {}
        self.websocket_sessions: Dict[WebSocketClientProtocol, SocketSession] = {}

        self.database: Database = Database("data/database.db")

        self.default_settings = {
            "rsa": {
                "keyfile": "data/rsa.key",
                "keysize": 4096
            },
            "webserver": {
                "host": "0.0.0.0",
                "port": 5000
            },
            "socketserver": {
                "host": "0.0.0.0",
                "port": 5001
            }
        }

        self.oa: OgladajAnime_pl = None

        if prepare:
            self.prepare()

    def prepare(self):
        self.settings = self.load_settings()
        
        self.rsa = RSACipher()
        if self.settings['rsa']['keyfile'] and Path(self.settings['rsa']['keyfile']).exists():
            with open(self.settings['rsa']['keyfile'], "rb") as f:
                key_data = json.loads(base64.b64decode(f.read()))
            self.rsa.import_public_key(key_data['public'])
            self.rsa.import_private_key(key_data['private'])
        else:
            keypair = self.rsa.generate_keypair(self.settings['rsa']['keysize'])
            with open(self.settings['rsa']['keyfile'], "wb") as f:
                f.write(base64.b64encode(json.dumps({"private": keypair[0], "public": keypair[1]}).encode()))
        
        host = self.settings['socketserver']['host'] if self.settings['socketserver']['host'] != self.settings['webserver']['host'] and not self.settings['socketserver']['host'] == "0.0.0.0" else ""
        self.webserver.add_path("/", ["POST"], APIExtender(socket_host=host, socket_port=self.settings['socketserver']['port'], public_rsa_key=self.rsa.public_key()))
        self.webserver.extend(WebExtender(database=self.database))

        if not Path("data/oa-headers.json").exists():
            print(Fore.RED + "Missing headers for OglądajAnime.pl. Please provide them in data/oa-headers.json." + Color.RESET)

        Requester("oa-requester",
            default_headers={
                "Host": "ogladajanime.pl",
                "Origin": "https://ogladajanime.pl",
                "Referer": "https://ogladajanime.pl",
                "X-Requested-With": "XMLHttpRequest",
                **(json.loads(open("data/oa-headers.json").read()) if Path("data/oa-headers.json").exists() else {})
            },
            max_requests_per_minute=20, max_requests_per_second=20,
            default_user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
        )

        Requester("cda.main",
         default_user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3")

        self.database.create_table("users", [
            "id TEXT PRIMARY KEY UNIQUE NOT NULL",
            "username TEXT NOT NULL",
            "email TEXT NOT NULL UNIQUE",
            "displayname TEXT NOT NULL",
            "password TEXT NOT NULL",
            "salt TEXT NOT NULL",
            "token TEXT NOT NULL",
            "settings TEXT NOT NULL DEFAULT '{}'",
            "image BLOB",
            "last_login DATETIME NOT NULL",
            "created DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP",
            "confirmed BOOLEAN NOT NULL DEFAULT FALSE",
            "deleted BOOLEAN NOT NULL DEFAULT FALSE",
            "suspended BOOLEAN NOT NULL DEFAULT FALSE"
        ])

        self.database.create_table("content", [
            "uid TEXT PRIMARY KEY UNIQUE NOT NULL",
            "origin_url TEXT NOT NULL",

            # For search purposes
            "searchable BOOLEAN NOT NULL DEFAULT TRUE",
            "source TEXT NOT NULL", #eg. ogladajanime, netflix, hulu
            "type TEXT NOT NULL", #eg. movie, series, episode, thumbnail
            "weight REAL NOT NULL",
            "title TEXT NOT NULL",

            # actual content entry, because it might differ from service to service
            "meta TEXT NOT NULL DEFAULT '{}'",
        ])

        self.database.create_table("media", [
            "id INTEGER PRIMARY KEY AUTOINCREMENT",
            "refer_id TEXT REFERENCES content(uid) NOT NULL",
            "requires_token BOOLEAN NOT NULL DEFAULT TRUE",
            
            "media_type TEXT NOT NULL", #eg. video, image, audio
            "media_format TEXT NOT NULL",
            "media_name TEXT NOT NULL", #eg. thumbnail, video, opening, etc. Used for geting through url.
            "media_id INT NOT NULL", #for when there is more than one media of the same type for the same content, eg. multiple resolutions or thumbnails.
            "lookup_meta TEXT NOT NULL DEFAULT '{}'", #used for searching for the media, eg. resolution, quality, etc.
            # /media/{refer_id}/{media_name}[?format={format}][&id={media_id}][&meta_arg=meta_val]: /media/1234/thumbnail, /media/1234/opening?format=mp4, /media/1234/video?format=mp4&id=1080p, /media/1234/thumbnail?id=1
            
            "origin_url TEXT UNIQUE DEFAULT NULL",
            "data BLOB DEFAULT NULL",
            "refers_to TEXT REFERENCES media(id) DEFAULT NULL",
        ])

        self.database.create_table("small_tokens", [
            "id INTEGER PRIMARY KEY AUTOINCREMENT",

            "user_id TEXT REFERENCES users(id) NOT NULL",
            "media_id TEXT REFERENCES media(id) NOT NULL",
            "token TEXT NOT NULL",
            "created DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP",
            "expires DATETIME NOT NULL"
        ])

        self.oa = OgladajAnime_pl(database=self.database, requester=Requester.get_requester("oa-requester"))

    def load_settings(self, settings_path: str = "data/settings.json") -> dict:
        # Loads, checks if valid and corrects settings if necessary
        def validator(settings: dict, parent_path: Optional[List[str]] = None, validate_to: dict = self.default_settings) -> Union[Literal[True], List[Tuple[List[str], Any]]]:
            missing = []
            for key in validate_to.keys():
                if not key in settings.keys() or type(settings[key]) != type(validate_to[key]):
                    missing.append(((parent_path or []) + [key], validate_to[key]))
                    continue

                if type(validate_to[key]) == dict:
                    validated = validator(settings[key], (parent_path or []) + [key], validate_to[key])
                    if validated != True:
                        missing.extend(validated)

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

            return settings

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
            
            while True:
                response = input().lower()
                if response in ["y", "yes"]:
                    settings = compliment(settings, validated)
                    with open(settings_path, "w") as f:
                        json.dump(self.default_settings, f, indent=4)
                    print(f"Settings saved to {Fore.YELLOW}{settings_path}{Color.RESET}.")
                    return settings
                elif response in ["n", "no"]:
                    print(f"Settings not saved, but will be used during runtime.")
                    settings = compliment(settings, validated)
                    return settings
                else:
                    print(f"Invalid input. Please try again: ", end="")
        
        return settings

    async def detach(self, callback: Callable, executor: Union[Callable, Thread] = Thread, *args, **kwargs) -> Thread:
        thread = executor(target=callback, args=args, kwargs=kwargs)
        thread.start()
        return thread

    async def handle_websocket(self, websocket: WebSocketClientProtocol) -> None:
        class CouldNotLoadData(Exception):
            pass

        async def decrypt(data: bytes, session: SocketSession) -> dict:
            data = data.decode("utf-8") if isinstance(data, bytes) else data
            try:
                return json.loads(data)
            except:
                pass

            if session.state >= SocketSession.State.ENCRYPTED and session.encryption_state == SocketSession.EncryptionState.AES_ENCRYPTED:
                try:
                    iv, data = data.split("::")
                    iv = self.rsa.decrypt(iv).decode("utf-8")
                    data = aes_cipher.decrypt(data, iv, base64.b64decode(session.aes_key))
                    return json.loads(data)
                except:
                    pass
            
            try:
                data = self.rsa.decrypt(data)
                return json.loads(data)
            except:
                pass

            if session.state >= SocketSession.State.ENCRYPTED:
                await send_error(websocket, session, "Could not read data.")
                raise CouldNotLoadData
            
            return data

        socket_id = generate_id(avoid=list(self.websocket_sessions.keys()))
        self.websocket_sessions[socket_id] = SocketSession()
        session = self.websocket_sessions[socket_id]

        session.state = SocketSession.State.CONNECTED
        session.socket = websocket
        session.id = socket_id
        session.address = websocket.remote_address
        session.public_rsa_key = None
        session.aes_key = None

        aes_cipher = AESCipher(False)

        while True:
            try:
                data: Union[dict, str] = await decrypt(await websocket.recv(), session)
            except (websockets.exceptions.ConnectionClosedError, websockets.exceptions.ConnectionClosedOK):
                break
            except CouldNotLoadData:
                asyncio.create_task(send_error(websocket, session, "Could not read data."))
                continue

            if data.get('action') == 'get-rsa-key':
                asyncio.create_task(get_rsa_key(session, websocket, self.rsa))
                continue

            if not data.get('data'):
                asyncio.create_task(send_error(websocket, session, "Invalid data."))
                print(f"Received invalid data: {data}")
                continue

            if data.get('action') == 'send-rsa-key':
                asyncio.create_task(send_rsa_key(session, websocket, data))
                continue

            if data.get('action') == 'send-aes-key':
                asyncio.create_task(send_aes_key(session, websocket, data))
                continue

            if data.get('action') == 'get-salt':
                asyncio.create_task(get_salt(session, websocket, data, self.database))
                continue

            if data.get('action') == 'get-user-auth':
                asyncio.create_task(get_user_auth(session, websocket, data, self.database))
                continue

            if data.get('action') == 'login':
                asyncio.create_task(login(session, websocket, data, self.database))
                continue
                
            if data.get('action') == 'register':
                asyncio.create_task(register(session, websocket, data, self.database))
                continue

            if data.get('action') == 'get-user-info':
                asyncio.create_task(get_user_info(session, websocket, data, self.database))
                continue

            if data.get('action') == 'get-search-suggestions':
                asyncio.create_task(get_search_suggestions(session, websocket, data, self.oa))
                continue

            if data.get('action') == 'search':
                asyncio.create_task(search(session, websocket, data, self.oa, self.database))
                continue

            if data.get('action') == 'get-content-info':
                asyncio.create_task(get_content_info(session, websocket, data, self.oa, self.database))
                continue

            if data.get('action') == 'get-service-info':
                asyncio.create_task(get_service_info(session, websocket, data, [self.oa]))
                continue

            if data.get('action') == 'get-player-info':
                asyncio.create_task(get_player_info(session, websocket, data, [self.oa], self.database))
                continue
            
            print(f"Received: {data}")

        try:
            del self.websocket_sessions[websocket]
        except:
            pass

    async def start(self):
        self.websocketserver.start(host=self.settings['socketserver']['host'], port=self.settings['socketserver']['port'], handler=self.handle_websocket, as_thread=True)
        self.webserver.run(self.settings['webserver']['host'], self.settings['webserver']['port'])

async def main():
    Requester("oa-requester",
     default_headers={
        "Referer": "https://ogladajanime.pl",
        "X-Requested-With": "XMLHttpRequest"
     },
     max_requests_per_minute=20, max_requests_per_second=20,
     default_user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
    )

    scrapper = OgladajAnime_pl(requester=Requester.get_requester("oa-requester"))
    with open("search.json", "w") as file:
        file.write(json.dumps([x.info() for x in await scrapper.search("My Hero Academia")], indent=4))

if __name__ == "__main__":
    asyncio.run(ProgramController(prepare=True).start())
    #asyncio.run(main())
    
#TODO: Asynchronously download thumbnails in background, and if already downloaded serve own url instead of upstream
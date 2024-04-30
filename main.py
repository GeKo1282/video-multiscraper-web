import json, os, base64, asyncio, threading, sys
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
from scripts.helper.downloader import Downloader

class ProgramController:
    def __init__(self, prepare: bool = False):
        self.webserver: WebServer = WebServer()
        self.websocketserver: WebSocketServer = WebSocketServer()
        self.downloader: Downloader = None

        self.rsa: RSACipher = None

        self.settings: dict = {}
        self.websocket_sessions: Dict[WebSocketClientProtocol, SocketSession] = {}

        self.database: Database = None

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
            },
            "database": {
                "path": "data/database.db",
                "media_token_lifetime": 3600
            },
            "downloaders": {
                "video": {
                    "path_prefix": "[auto]",
                    "limit_per_referer": 1,
                }
            }
        }

        self.oa: OgladajAnime_pl = None

        if prepare:
            self.prepare()

    async def prepare(self):
        self.settings = self.load_settings()

        self.database = Database(self.settings['database']['path'])
        
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

        if not Path("data/oa-headers.json").exists():
            print(Fore.RED + "Missing headers for OglądajAnime.pl. Please provide them in data/oa-headers.json." + Color.RESET)

        oa_requester = Requester("oa-requester",
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
            "last_login INTEGER NOT NULL",
            "created INTEGER NOT NULL",
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
            "uid TEXT UNIQUE DEFAULT NULL",
            "refer_id TEXT REFERENCES content(uid) NOT NULL",
            "requires_token BOOLEAN NOT NULL DEFAULT TRUE",

            "download_priority REAL NOT NULL DEFAULT 0", #Indicates the order in which the media should be downloaded, 0 meaining it won't be downloaded at all.
            "metadata TEXT NOT NULL DEFAULT '{}'", #used for storing metadata about the media, eg. length, resolution, quality, etc.
            
            "media_type TEXT NOT NULL", #eg. video, image, audio
            "media_format TEXT",
            "media_name TEXT NOT NULL", #eg. thumbnail, video, opening, etc. Used for geting through url.
            "media_id TEXT NOT NULL", #for when there is more than one media of the same type for the same content, eg. multiple resolutions or thumbnails.
            # /media/{refer_id}/{media_name}[?format={format}][&id={media_id}][&meta_arg=meta_val]: /media/1234/thumbnail, /media/1234/opening?format=mp4, /media/1234/video?format=mp4&id=1080p, /media/1234/thumbnail?id=1
            
            "origin_url TEXT DEFAULT NULL",
            "data_path TEXT UNIQUE DEFAULT NULL",
            "refers_to TEXT REFERENCES media(id) DEFAULT NULL",

            "UNIQUE(refer_id, media_name, media_id)",
            "UNIQUE(refer_id, origin_url)"
        ])

        self.database.create_table("media_tokens", [
            "id INTEGER PRIMARY KEY AUTOINCREMENT",

            "user_id TEXT REFERENCES users(id) NOT NULL",
            "media_id TEXT REFERENCES media(id) NOT NULL",
            "token TEXT NOT NULL",
            "created INTEGER NOT NULL DEFAULT CURRENT_TIMESTAMP",
            "expires INTEGER NOT NULL"
        ])

        self.database.create_table("temporary_media_data", [
            "id INTEGER PRIMARY KEY AUTOINCREMENT",
            "media_id INT REFERENCES media(id) NOT NULL",
            "start_byte INTEGER NOT NULL",
            "end_byte INTEGER NOT NULL",
            "data BLOB NOT NULL",
            "UNIQUE(media_id, start_byte, end_byte)"
        ])

        self.oa = OgladajAnime_pl(database=self.database, requester=Requester.get_requester("oa-requester"))
        self.downloader = Downloader(self.database, [self.oa], max_downloaders=20)

        host = self.settings['socketserver']['host'] if self.settings['socketserver']['host'] != self.settings['webserver']['host'] and not self.settings['socketserver']['host'] == "0.0.0.0" else ""
        self.webserver.add_path("/", ["POST"], APIExtender(socket_host=host, socket_port=self.settings['socketserver']['port'], public_rsa_key=self.rsa.public_key()))
        self.webserver.extend(WebExtender(database=self.database, downloader=self.downloader))

        if any([arg == "--debug-mode" for arg in sys.argv]):
            return True

        try:
            data = "id=207638"
            player_list = json.loads(json.loads((await oa_requester.post(self.oa.player_list_url, headers={
                "Referer": "https://ogladajanime.pl/anime/moja-akademia-bohaterow-6",
                "Content-Length": str(len(data.encode())),
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"
            }, data=data))['text'])['data'])

            if not player_list['players']:
                print(Fore.RED + "Got empty test data from OglądajAnime.pl! Exitting, please check credentials aren't being rate limited." + Color.RESET)
                return False
        except Exception as e:
            print(Fore.RED + "Couldn't get test data from OglądajAnime.pl! Exitting, please check credentials and if you aren't being rate limited: " + str(e) + Color.RESET)
            return False

        return True

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

        if settings['downloaders']['video']['path_prefix'] == "[auto]":
            settings['downloaders']['video']['path_prefix'] = Path("media").absolute()

        if not Path(settings['downloaders']['video']['path_prefix']).exists():
            os.makedirs(settings['downloaders']['video']['path_prefix'], exist_ok=True)
        
        return settings

    def detach(self, callback: Callable, executor: Union[Callable, Thread] = Thread, *args, **kwargs) -> Thread:
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

        session.media_token_lifetime = self.settings['database']['media_token_lifetime']

        aes_cipher = AESCipher(False)

        #TODO: Tryexcept all the things and send "Unknown error" if something goes wrong

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

            if data.get('action') == 'get-players-meta':
                asyncio.create_task(get_players_meta(session, websocket, data, [self.oa], self.database))
                continue

            if data.get('action') == 'get-player-data':
                asyncio.create_task(get_player_data(session, websocket, data, [self.oa], self.database))
                continue

            if data.get('action') == 'get-media-token':
                asyncio.create_task(get_media_token(session, websocket, data, self.database))
                continue

            if data.get('action') == 'download-media':
                asyncio.create_task(download_media(session, websocket, data, self.database))
                continue
            
            print(f"Received: {data}")

        try:
            del self.websocket_sessions[websocket]
        except:
            pass

    async def start(self):
        self.downloader.start()
        self.websocketserver.start(host=self.settings['socketserver']['host'], port=self.settings['socketserver']['port'], handler=self.handle_websocket, as_thread=True)
        threading.Thread(self.webserver.run(host=self.settings['webserver']['host'], port=self.settings['webserver']['port'])).start()

async def main():
    pc = ProgramController(prepare=False)
    if not await pc.prepare():
        exit()
    await pc.start()

if __name__ == "__main__":
    asyncio.run(main())
    
#TODO: Asynchronously download thumbnails in background, and if already downloaded serve own url instead of upstream
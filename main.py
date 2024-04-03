import json, os, base64, asyncio
from typing import List, Optional, AnyStr, Tuple, Any, Literal, Union, Callable, Dict
from pathlib import Path
from threading import Thread
from datetime import datetime
from scripts.webserver import WebExtender
from scripts.scrappers import OgladajAnime_pl
from scripts.api import APIExtender
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

        Requester("oa-requester",
            default_headers={
                "Referer": "https://ogladajanime.pl",
                "X-Requested-With": "XMLHttpRequest"
            },
            max_requests_per_minute=20, max_requests_per_second=20,
            default_user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
        )

        self.oa = OgladajAnime_pl(requester=Requester.get_requester("oa-requester"))

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

        async def send_error(error: str, code: int = 0, action: str = None, additional: dict = None):
            # Codes table:
            # 0: Unknown / not specified error
            # 1-100: Reserved
            # 101-200: Login / register / authorization errors:
            #     101-110: Register errors
            #     111-120: Login errors
            #         111: Invalid credentials

            await WebSocketServer.send(websocket, {
                "error": error,
                "code": code,
                **({"action": action} if action else {}),
                **(additional or {})
            }, session)

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
                await send_error("Could not read data.")
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
            except CouldNotLoadData:"id = ?, email = ?, username = ?, displayname = ?, password = ?, token = ?, settings = ?, image = ?, last_login = ?, confirmed = ?, deleted = ?, suspended = ?",
            if data.get('action') == 'get-rsa-key':
                session.state = SocketSession.State.ENCRYPTED
                session.encryption_state = SocketSession.EncryptionState.INCOMING_RSA_ENCRYPTED
                await WebSocketServer.send(websocket, {
                    "action": "send-rsa-key",
                    "data": {
                        "key": self.rsa.public_key()
                    }
                }, session)
                continue

            if not data.get('data'):
                await send_error("Invalid data!")
                print(f"Received invalid data: {data}")
                continue

            if data.get('action') == 'send-rsa-key':
                if not data['data'].get('key'):
                    await send_error("Invalid data.", action=data.get('action'))
                    continue

                session.public_rsa_key = data['data']['key']
                session.state = SocketSession.State.ENCRYPTED
                session.encryption_state = SocketSession.EncryptionState.FULL_RSA_ENCRYPTED
                await WebSocketServer.send(websocket, {
                    "action": "receive-rsa-key",
                    "success": True
                }, session)
                continue

            if data.get('action') == 'send-aes-key':
                if not data['data'].get('key'):
                    await send_error("Invalid data.", action=data.get('action'))
                    continue

                session.aes_key = data['data']['key']
                session.state = SocketSession.State.ENCRYPTED
                session.encryption_state = SocketSession.EncryptionState.AES_ENCRYPTED
                await WebSocketServer.send(websocket, {
                    "action": "receive-aes-key",
                    "success": True
                }, session, rsa_only=True)
                continue

            if data.get('action') == 'get-salt':
                username = data['data'].get('username')
                if not username:
                    await send_error("Invalid data.", action=data.get('action'))
                    continue

                user = self.database.select("users", ["salt"], ("username = ?" if not "@" in username else "email = ?"), [username])
                if not user:
                    await send_error("User not found.", action=data.get('action'))
                    continue

                await WebSocketServer.send(websocket, {
                    "action": "get-salt",
                    "data": {
                        "salt": user[0][0]
                    },
                    "success": True
                }, session)

            if data.get('action') == 'get-user-auth':
                if not data['data'].get('username') or not data['data'].get('password'):
                    await send_error("Invalid data.", action=data.get('action'))
                    continue

                user = self.database.select("users", ["id", "password", "token"], ("username = ?" if not "@" in data['data']['username'] else "email = ?"), [data['data']['username']])
                if not user or not user[0][1] == data['data']['password']:
                    await send_error("Invalid credentials.", code=111, action=data.get('action'), additional={
                        "success": False
                    })
                    continue

                await WebSocketServer.send(websocket, {
                    "action": "send-user-auth",
                    "data": {
                        "id": user[0][0],
                        "token": user[0][2]
                    },
                    "success": True
                }, session)

                continue

            if data.get('action') == 'login':
                user_id, token = data['data'].get('id'), data['data'].get('token')

                if not user_id or not token:
                    await send_error("Invalid data.", action=data.get('action'))
                    continue

                user = self.database.select("users", ["id"], "id = ? AND token = ?", [user_id, token])
                if not user:
                    await send_error("Invalid credentials.", code=111, action=data.get('action'), additional={
                        "success": False
                    })
                    continue

                await WebSocketServer.send(websocket, {
                    "action": "login",
                    "success": True
                }, session)
                
            if data.get('action') == 'register':
                username, displayname, email, password, salt = \
                (data['data'].get('username'),
                data['data'].get('displayname'),
                data['data'].get('email'),
                data['data'].get('password'),
                data['data'].get('salt'))

                if not username or not displayname or not email or not password:
                    await send_error("Invalid data.", action=data.get('action'))
                    continue

                if self.database.select("users", ["id"], "username = ? OR email = ?", [username, email]):
                    await send_error("Username or email already in use.", code=101, action=data.get('action'),
                    additional={
                        "success": False
                    })
                    continue

                user_id = generate_id(avoid=[x[0] for x in self.database.select("users", ["id"])])
                user_token = hex(int(datetime.now().timestamp()))[2:] + sha512(user_id)[:24] + generate_id(length=32, type="hex")

                self.database.insert("users",
                ["id", "email", "username", "displayname", "password", "salt", "token", "settings", "image", "last_login", "confirmed", "deleted", "suspended"],
                [user_id, email, username, displayname, password, salt, user_token, "{}", None, datetime.now(), True, False, False])

                await WebSocketServer.send(websocket, {
                    "action": "send-user-auth",
                    "data": {
                        "id": user_id,
                        "token": user_token
                    },
                    "success": True
                }, session)

            if data.get('action') == 'get-user-info':
                if any([not data['data'].get(field) for field in ['id', 'token']]):
                    await send_error("Invalid data.", action=data.get('action'))
                    continue

                user = self.database.select("users", ["username", "email", "displayname", "created"], "id = ? AND token = ?", [data['data']['id'], data['data']['token']])

                if not user:
                    await send_error("Invalid credentials.", code=111, action=data.get('action'), additional={
                        "success": False
                    })
                    continue

                await WebSocketServer.send(websocket, {
                    "action": "send-user-info",
                    "data": {
                        "username": user[0][0],
                        "email": user[0][1],
                        "displayname": user[0][2],
                        "created": user[0][3],
                        "avatar": f"/cdn/user/{data['data']['id']}/avatar"
                    },
                    "success": True
                }, session)

            print(f"Received: {data}")

        del self.websocket_sessions[websocket]

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
    
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from scripts.helper.socket import WebSocketServer, SocketSession
from scripts.helper.cipher import RSACipher
from scripts.helper.database import Database
from scripts.helper.util import generate_id, sha512
from scripts.scrappers import Service, OgladajAnime_pl
from websockets import WebSocketClientProtocol
from datetime import datetime
from typing import List, Tuple, Optional

async def send_error(websocket: WebSocketClientProtocol, session: SocketSession, error: str, code: int = 0, action: str = None, additional: dict = None):
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

async def get_rsa_key(session: SocketSession, websocket: WebSocketClientProtocol, rsa: RSACipher):
    session.state = SocketSession.State.ENCRYPTED
    session.encryption_state = SocketSession.EncryptionState.INCOMING_RSA_ENCRYPTED
    await WebSocketServer.send(websocket, {
        "action": "send-rsa-key",
        "data": {
            "key": rsa.public_key()
        }
    }, session)

async def send_rsa_key(session: SocketSession, websocket: WebSocketClientProtocol, data: dict):
    if not data['data'].get('key'):
        await send_error(websocket, session, "Invalid data.", action=data.get('action'))
        return

    session.public_rsa_key = data['data']['key']
    session.state = SocketSession.State.ENCRYPTED
    session.encryption_state = SocketSession.EncryptionState.FULL_RSA_ENCRYPTED
    await WebSocketServer.send(websocket, {
        "action": "receive-rsa-key",
        "success": True
    }, session)

async def send_aes_key(session: SocketSession, websocket: WebSocketClientProtocol, data: dict):
    if not data['data'].get('key'):
        await send_error("Invalid data.", action=data.get('action'))
        return

    session.aes_key = data['data']['key']
    session.state = SocketSession.State.ENCRYPTED
    session.encryption_state = SocketSession.EncryptionState.AES_ENCRYPTED
    await WebSocketServer.send(websocket, {
        "action": "receive-aes-key",
        "success": True
    }, session, rsa_only=True)

async def get_salt(session: SocketSession, websocket: WebSocketClientProtocol, data: dict, database: Database):
    username = data['data'].get('username')
    if not username:
        await send_error(websocket, session, "Invalid data.", action=data.get('action'))
        return

    user = database.select("users", ["salt"], ("username = ?" if not "@" in username else "email = ?"), [username])
    if not user:
        await send_error(websocket, session, "User not found.", action=data.get('action'))
        return

    await WebSocketServer.send(websocket, {
        "action": "get-salt",
        "data": {
            "salt": user[0][0]
        },
        "success": True
    }, session)

async def get_user_auth(session: SocketSession, websocket: WebSocketClientProtocol, data: dict, database: Database):
    if not data['data'].get('username') or not data['data'].get('password'):
        await send_error(websocket, session, "Invalid data.", action=data.get('action'))
        return

    user = database.select("users", ["id", "password", "token"], ("username = ?" if not "@" in data['data']['username'] else "email = ?"), [data['data']['username']])
    if not user or not user[0][1] == data['data']['password']:
        await send_error(websocket, session, "Invalid credentials.", code=111, action=data.get('action'), additional={
            "success": False
        })
        return

    await WebSocketServer.send(websocket, {
        "action": "send-user-auth",
        "data": {
            "id": user[0][0],
            "token": user[0][2]
        },
        "success": True
    }, session)

async def login(session: SocketSession, websocket: WebSocketClientProtocol, data: dict, database: Database):
    user_id, token = data['data'].get('id'), data['data'].get('token')

    if not user_id or not token:
        await send_error(websocket, session, "Invalid data.", action=data.get('action'))
        return

    user = database.select("users", ["id"], "id = ? AND token = ?", [user_id, token])
    if not user:
        await send_error(websocket, session, "Invalid credentials.", code=111, action=data.get('action'), additional={
            "success": False
        })
        return

    await WebSocketServer.send(websocket, {
        "action": "login",
        "success": True
    }, session)

async def register(session: SocketSession, websocket: WebSocketClientProtocol, data: dict, database: Database):
    username, displayname, email, password, salt = \
                (data['data'].get('username'),
                data['data'].get('displayname'),
                data['data'].get('email'),
                data['data'].get('password'),
                data['data'].get('salt'))

    if not username or not displayname or not email or not password:
        await send_error(websocket, session, "Invalid data.", action=data.get('action'))
        return

    if database.select("users", ["id"], "username = ? OR email = ?", [username, email]):
        await send_error(websocket, session, "Username or email already in use.", code=101, action=data.get('action'),
        additional={
            "success": False
        })
        return

    user_id = generate_id(avoid=[x[0] for x in database.select("users", ["id"])])
    user_token = hex(int(datetime.now().timestamp()))[2:] + sha512(user_id)[:24] + generate_id(length=32, type="hex")

    database.insert("users",
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

async def get_user_info(session: SocketSession, websocket: WebSocketClientProtocol, data: dict, database: Database):
    if any([not data['data'].get(field) for field in ['id', 'token']]):
        await send_error(websocket, session, "Invalid data.", action=data.get('action'))
        return

    user = database.select("users", ["username", "email", "displayname", "created"], "id = ? AND token = ?", [data['data']['id'], data['data']['token']])

    if not user:
        await send_error(websocket, session, "Invalid credentials.", code=111, action=data.get('action'), additional={
            "success": False
        })
        return

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

async def get_search_suggestions(session: SocketSession, websocket: WebSocketClientProtocol, data: dict, oa: OgladajAnime_pl):    
    query: str = data['data'].get('query')
    if not query:
        await send_error(websocket, session, "Invalid data.", action=data.get('action'))
        return

    # Hard limit maximum suggestions to 20
    limit = min(data['data'].get('limit', 5), 20)

    # vectorizer = TfidfVectorizer()
    # suggestions_vectors = vectorizer.fit_transform(suggestions)
    # query_vector = vectorizer.transform([query])

    # similarities = cosine_similarity(query_vector, suggestions_vectors)

    # ranked_suggestions = [(suggestion, similarity) for suggestion, similarity in zip(suggestions, similarities[0])]
    # ranked_suggestions.sort(key=lambda x: x[1], reverse=True)

    await WebSocketServer.send(websocket, {
        "action": "send-search-suggestions",
        "data": {
            "query": query,
            "suggestions": await oa.get_search_suggestions(query, limit)
        },
        "success": True
    }, session, unencrypted=True)

async def search(session: SocketSession, websocket: WebSocketClientProtocol, data: dict, services: List[Service], database: Database):
    query, limit, start, provider, categorize, user_id, token = \
    (data['data'].get('query'),
    min(data['data'].get('limit', 10), 100),
    data['data'].get('start', 0),
    data['data'].get('provider', 'all'),
    data['data'].get('categorize', "mixed"),
    data['data'].get('id'),
    data['data'].get('token'))

    if not user_id or not token or not query:
        await send_error(websocket, session, "Invalid data.", action=data.get('action'))
        return
    
    user = database.select("users", ["id"], "id = ? AND token = ?", [user_id, token])

    if not user:
        await send_error(websocket, session, "Invalid credentials.", code=111, action=data.get('action'), additional={
            "success": False
        })
        return
    


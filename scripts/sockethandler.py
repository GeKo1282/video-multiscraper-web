import json
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from scripts.helper.socket import WebSocketServer, SocketSession
from scripts.helper.cipher import RSACipher
from scripts.helper.database import Database
from scripts.helper.util import generate_id, sha512
from scripts.scrappers import OgladajAnime_pl, OA_Movie, OA_Series, Service, Movie, Series, Episode
from websockets import WebSocketClientProtocol
from datetime import datetime, timedelta
from typing import List, Union, Optional

def authorize_user(id: str, token: str, database: Database) -> bool:
    return bool(database.select("users", ["id"], "id = ? AND token = ?", [id, token]))

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
    ["id", "email", "username", "displayname", "password", "salt", "token", "settings", "image", "last_login", "created", "confirmed", "deleted", "suspended"],
    [user_id, email, username, displayname, password, salt, user_token, "{}", None, int(datetime.now().timestamp()), int(datetime.now().timestamp()), True, False, False]
    )

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

async def search(session: SocketSession, websocket: WebSocketClientProtocol, data: dict, oa: OgladajAnime_pl, database: Database):
    query: str = data['data'].get('query')
    user_id = data['data'].get('user_id', "")
    token = data['data'].get('token', "")

    if not authorize_user(user_id, token, database):
        await send_error(websocket, session, "Invalid credentials.", code=111, action=data.get('action'), additional={
            "success": False
        })
        return

    if not query:
        await send_error(websocket, session, "Invalid data.", action=data.get('action'))
        return

    await WebSocketServer.send(websocket, {
        "action": "send-search-results",
        "data": {
            "query": query,
            "results": [result.info() for result in await oa.search(query, True)]
        },
        "success": True
    }, session)

async def get_content_info(session: SocketSession, websocket: WebSocketClientProtocol, data: dict, oa: OgladajAnime_pl, database: Database):
    content_uid = data['data'].get('content_uid')
    media_uid = data['data'].get('media_uid')
    preffered_type = data['data'].get('preffered_type')
    scrape = data['data'].get('scrape', True)
    user_id = data['data'].get('user_id', "")
    token = data['data'].get('token', "")

    if not authorize_user(user_id, token, database):
        await send_error(websocket, session, "Invalid credentials.", code=111, action=data.get('action'), additional={
            "success": False
        })
        return
    
    if not content_uid and not media_uid:
        await send_error(websocket, session, "Invalid data.", action=data.get('action'))
        return
    
    if content_uid:
        content = oa.get_by_uid(content_uid, True, True)

        if type(content) in [OA_Movie, OA_Series] and not content.is_scrapped and scrape:
            content = await content.scrape()

    else:
        media = database.select("media", ["refer_id"], "uid = ?", [media_uid])
        if not media:
            await send_error(websocket, session, "Media not found.", action=data.get('action'))
            return
        
        content = oa.get_by_uid(media[0][0], True, True)

        if type(content) in [OA_Movie, OA_Series] and not content.is_scrapped and scrape:
            content = await content.scrape()

    if isinstance(content, Episode) and preffered_type.lower() == "series":
        content = content.series
        if not content.is_scrapped and scrape:
            content = await content.scrape()

    await WebSocketServer.send(websocket, {
        "action": "send-content-info",
        "data": content.info("JSON", True, True),
        "success": True
    }, session)

async def get_service_info(session: SocketSession, websocket: WebSocketClientProtocol, data: dict, services: List[Service]):
    name = data['data'].get('name') or data['data'].get('service_name')

    if not name:
        await send_error(websocket, session, "Invalid data.", action=data.get('action'))
        return
    
    service = next((service for service in services if name in service.codenames), None)

    if not service:
        await send_error(websocket, session, "Service not found.", action=data.get('action'))
        return
    
    await WebSocketServer.send(websocket, {
        "action": "send-service-info",
        "data": service.info(),
        "success": True
    }, session, unencrypted=True)

async def get_players_meta(session: SocketSession, websocket: WebSocketClientProtocol, data: dict, services: List[Service], database: Database):
    uid = data['data'].get('content_uid')
    user_id = data['data'].get('user_id', "")
    token = data['data'].get('token', "")

    if not uid or not user_id or not token:
        await send_error(websocket, session, "Invalid data.", action=data.get('action'))
        return

    if not authorize_user(user_id, token, database):
        await send_error(websocket, session, "Invalid credentials.", code=111, action=data.get('action'), additional={
            "success": False
        })
        return
    
    content = database.select("content", ["source"], "uid = ?", [uid])

    if not content:
        await send_error(websocket, session, "Content not found.", action=data.get('action'))
        return
    
    service = next((service for service in services if content[0][0] in service.codenames), None)

    content = service.get_by_uid(uid, False, False)

    if isinstance(content, Series):
        if not content.is_scrapped:
            content = await content.scrape()

        if not isinstance(content, Series):
            episode: Union[Episode, Movie] = content

        episode: Episode = content.episodes[0]
    else:
        episode: Union[Episode, Movie] = content

    await episode.get_sources(scrape=False)

    return await WebSocketServer.send(websocket, {
        "action": "send-players-meta",
        "data": episode.info("JSON"),
        "success": True
    }, session)

async def get_player_data(session: SocketSession, websocket: WebSocketClientProtocol, data: dict, services: List[Service], database: Database):
    media_uid = data['data'].get('media_uid')
    scrape = data['data'].get('scrape', False)
    user_id = data['data'].get('user_id', "")
    token = data['data'].get('token', "")
    
    async def enrich_media_token(source_info: dict) -> dict:
        media_token = await get_media_token(session, websocket, {
            "data": {
                "media_uid": source_info['uid'],
                "user_id": user_id,
                "token": token
            }
        }, database, return_data=True)

        source_info['media_token'] = {
            "token": media_token['token'],
            "expires": media_token['expires']
        }

        source_info['url'] = source_info['url'] + "&token=" + media_token['token'] if "?" in source_info['url'] else source_info['url'] + "?token=" + media_token['token']

        return source_info

    if not media_uid or not user_id or not token:
        await send_error(websocket, session, "Invalid data.", action=data.get('action'))
        return
    
    if not authorize_user(user_id, token, database):
        await send_error(websocket, session, "Invalid credentials.", code=111, action=data.get('action'), additional={
            "success": False
        })
        return
    
    media = database.select("media", ["refer_id"], "uid = ?", [media_uid])

    if not media:
        await send_error(websocket, session, "Media not found.", action=data.get('action'))
        return
    
    content = database.select("content", ["source", "meta"], "uid = ?", [media[0][0]])

    if not content:
        await send_error(websocket, session, "Content not found.", action=data.get('action'))
        return
    
    service = next((service for service in services if content[0][0] in service.codenames), None)
    episode = service.get_by_uid(media[0][0], False, False)

    if not episode:
        await send_error(websocket, session, "Episode not found.", action=data.get('action'))
        return

    if scrape:
        await episode.get_sources(scrape=True, scrape_one=True, force_scrape=[str(media_uid)])

    return await WebSocketServer.send(websocket, {
        "action": "send-player-data",
        "data": await enrich_media_token(next((source for source in episode.info("JSON")['sources'] if str(source['uid']) == str(media_uid)), None)),
        "success": True
    }, session)

async def get_media_token(session: SocketSession, websocket: WebSocketClientProtocol, data: dict, database: Database, return_data: bool = False):
    media_uid = data['data'].get('media_uid')
    user_id = data['data'].get('user_id', "")
    token = data['data'].get('token', "")

    if not media_uid or not user_id or not token:
        await send_error(websocket, session, "Invalid data.", action=data.get('action'))
        return
    
    if not authorize_user(user_id, token, database):
        await send_error(websocket, session, "Invalid credentials.", code=111, action=data.get('action'), additional={
            "success": False
        })
        return
    
    media = database.select("media", ["id"], "uid = ?", [media_uid])
    if not media:
        await send_error(websocket, session, "Media not found.", action=data.get('action'))
        return
    
    ttoken = database.select("media_tokens", ["token", "expires"], "media_id = ? AND user_id = ? AND expires > ?", [media[0][0], user_id, int((datetime.now() + timedelta(minutes=5)).timestamp())])

    if not ttoken:
        ttoken = generate_id()
        expires = int((datetime.now() + timedelta(seconds=session.media_token_lifetime)).timestamp())

        database.insert("media_tokens", ["media_id", "user_id", "token", "created", "expires"], [media[0][0], user_id, ttoken, int(datetime.now().timestamp()), expires])
    else:
        ttoken, expires = ttoken[0]

    if return_data:
        return {
            "token": ttoken,
            "expires": expires
        }
    
    await WebSocketServer.send(websocket, {
        "action": "send-media-token",
        "data": {
            "token": ttoken,
            "expires": expires
        },
        "success": True
    }, session)

async def download_media(session: SocketSession, websocket: WebSocketClientProtocol, data: dict, database: Database):
    uid = data['data'].get('content_uid')
    user_id = data['data'].get('user_id', "")
    token = data['data'].get('token', "")

    if not uid or not user_id or not token:
        await send_error(websocket, session, "Invalid data.", action=data.get('action'))
        return
    
    if not authorize_user(user_id, token, database):
        await send_error(websocket, session, "Invalid credentials.", code=111, action=data.get('action'), additional={
            "success": False
        })
        return
    
    content = database.select("media", ["refer_id"], "uid = ?", [uid])

async def update_watch_progress(session: SocketSession, websocket: WebSocketClientProtocol, data: dict, database: Database):
    content_uid = data['data'].get('content_uid') or data['data'].get('uid')
    user_id = data['data'].get('user_id', "")
    token = data['data'].get('token', "")
    progress = data['data'].get('progress')

    if not content_uid or not user_id or not token or not progress:
        await send_error(websocket, session, "Invalid data.", action=data.get('action'))
        return
    
    if not authorize_user(user_id, token, database):
        await send_error(websocket, session, "Invalid credentials.", code=111, action=data.get('action'), additional={
            "success": False
        })
        return
    
    id = database.select("watch_progress", ["id"], "content_id = ? AND user_id = ?", [content_uid, user_id])

    if id:
        database.update("watch_progress", ["progress", "updated_at"], [int(progress), int(datetime.now().timestamp())], "id = ?", [id[0][0]])
    else:
        database.insert("watch_progress", ["user_id", "content_id", "progress", "updated_at"], [user_id, content_uid, int(progress), int(datetime.now().timestamp())])

    await WebSocketServer.send(websocket, {
        "action": "update-watch-progress",
        "success": True
    }, session)

async def get_watch_progress(session: SocketSession, websocket: WebSocketClientProtocol, data: dict, database: Database):
    content_uid = data['data'].get('content_uid') or data['data'].get('uid')
    user_id = data['data'].get('user_id', "")
    token = data['data'].get('token', "")
    top_level = data['data'].get('top_level', False)

    if not user_id or not token:
        await send_error(websocket, session, "Invalid data.", action=data.get('action'))
        return
    
    if not authorize_user(user_id, token, database):
        await send_error(websocket, session, "Invalid credentials.", code=111, action=data.get('action'), additional={
            "success": False
        })
        return
    
    if content_uid:
        progress_data = database.select("watch_progress", ["content_id", "progress"], "user_id = ? AND content_id = ?", [user_id, content_uid])
    else:
        progress_data = database.select("watch_progress", ["content_id", "progress"], "user_id = ?", [user_id])

    if not progress_data and content_uid:
        await send_error(websocket, session, "Invalid request!", code=112, action=data.get('action'), additional={
            "success": False
        })

    to_return = []
    for entry in progress_data:
        total = [*[duration for duration in database.select("media", ["media_duration"], "refer_id = ? AND media_type='video'", [entry[0]]) if duration], None][0]
        total = total[0] if total and total[0] else "N/A"
        to_return.append({
            "uid": entry[0],
            "progress": entry[1],
            "total": total
        })

    if not top_level:
        await WebSocketServer.send(websocket, {
            "action": "get-watch-progress",
            "success": True,
            "data": to_return
        }, session)

    for index, entry in enumerate(to_return):
        parent = ((entry['uid'],),)
        while True:
            parent = database.select("content", ["parent_uid", "uid", "type", "self_index"], "uid = ?", [parent[0][0]])

            if not parent:
                break

            if parent[0][1] == entry['uid']:
                to_return[index] = {
                    **to_return[index],
                    "uid": parent[0][1],
                    "type": parent[0][2],
                    **({"index": parent[0][3]} if parent[0][3] else {})
                }
                continue

            to_return[index][parent[0][2]] = {
                "uid": parent[0][1],
                **({"index": parent[0][3]} if parent[0][3] else {})
            }


    await WebSocketServer.send(websocket, {
        "action": "get-watch-progress",
        "success": True,
        "data": to_return
    }, session)

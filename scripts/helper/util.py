import random, requests, json
from typing import Union, Literal, List
from hashlib import sha512 as nonsalt_sha512

def generate_id(length: int = 16, type: Union[Literal["int"], Literal["str"], Literal["hex"]] = "str", *, charset: Union[str, List[str]] = None, avoid: List[Union[str, int]] = None) -> Union[str, int]:
    if type == "int":
        new = random.randint(10 ** (length - 1), 10 ** length - 1)
        while avoid and new in avoid:
            new = random.randint(10 ** (length - 1), 10 ** length - 1)
        return new
    
    if not charset:
        if type == "hex":
            charset = "0123456789abcdef"
        else:
            charset = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"

    new = "".join([random.choice(charset) for _ in range(length)])
    while avoid and new in avoid:
        new = "".join([random.choice(charset) for _ in range(length)])

    return new

def sha512(data: Union[str, bytes], salt: Union[str, bytes] = None) -> str:
    if isinstance(data, str):
        data = data.encode()
        
    if salt and isinstance(salt, str):
        salt = salt.encode()

    if salt:
        return nonsalt_sha512((data + salt)).hexdigest()
    
    return nonsalt_sha512(data).hexdigest()

def get_user_agents() -> List[str]:
    return json.loads(requests.get("https://cdn.jsdelivr.net/gh/microlinkhq/top-user-agents@master/src/index.json").text)

def sanitize(string: str) -> str:
    return string.replace("\t", "").strip("\n").strip()

def normalize(string: str):
    return string.replace(" ", "-").lower()
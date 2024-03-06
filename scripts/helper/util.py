import random
from typing import Union, Literal, List

def generate_id(length: int = 16, type: Union[Literal["int"], Literal["str"]] = "str", *, charset: str = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789", avoid: List[Union[str, int]] = None) -> Union[str, int]:
    if type == "int":
        new = random.randint(10 ** (length - 1), 10 ** length - 1)
        while avoid and new in avoid:
            new = random.randint(10 ** (length - 1), 10 ** length - 1)
        return new
    
    new = "".join([random.choice(charset) for _ in range(length)])
    while avoid and new in avoid:
        new = "".join([random.choice(charset) for _ in range(length)])

    return new
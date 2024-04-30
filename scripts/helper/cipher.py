import random, string, os
from typing import Union, Tuple
from base64 import b64encode, b64decode
from Crypto.Util.Padding import pad, unpad
from Crypto.Cipher import AES, PKCS1_OAEP
from Crypto.PublicKey import RSA
from Crypto.Hash import SHA256

class AESCipher():
    def __init__(self, generate_key: bool = False):
        self.key = self.generate_key() if generate_key else None

    def generate_key(self, length: int = 32):
        return "".join(random.choice(string.ascii_letters + string.digits) for _ in range(length))

    def encrypt(self, plaintext: Union[str, bytes], key: Union[str, bytes] = None, iv: Union[str, bytes] = None) -> Tuple[str, str]:
        key = key if key else self.key

        if type(key) == str:
            key = key.encode('utf-8')

        if not iv:
            iv = os.urandom(AES.block_size)
        
        if type(iv) == str:
            iv = iv.encode('utf-8')
        
        cipher = AES.new(key, AES.MODE_CBC, iv=iv)
        ct_bytes = cipher.encrypt(pad(plaintext if type(plaintext) == bytes else plaintext.encode(), AES.block_size))
        iv = b64encode(iv).decode('utf-8')
        ciphertext = b64encode(ct_bytes).decode('utf-8')
        return ciphertext, iv
    
    def decrypt(self, ciphertext:  Union[str, bytes], base64_encoded_iv: Union[str, bytes], key: Union[str, bytes] = None) -> bytes:
        key = key if key else self.key
        iv = b64decode(base64_encoded_iv)

        if type(key) == str:
            key = key.encode('utf-8')

        ciphertext_bytes = b64decode(ciphertext)
        cipher = AES.new(key, AES.MODE_CBC, iv)
        plaintext = unpad(cipher.decrypt(ciphertext_bytes), AES.block_size)
        return plaintext

class RSACipher():
    def __init__(self, generate_keypair: bool = False):
        self.keypair = self.generate_keypair() if generate_keypair else None

    def generate_keypair(self, key_length: int = 2048, set_keypair: bool = True) -> Tuple[str, str]:
        key = RSA.generate(key_length)
        private_key = key.export_key().decode()
        public_key = key.publickey().export_key().decode()

        if set_keypair:
            self.keypair = (private_key, public_key)
            
        return private_key, public_key
    
    def import_private_key(self, key: Union[str, bytes]) -> str:
        key = key if type(key) == str else key.decode('utf-8')
        if self.keypair:
            self.keypair = (key, self.keypair[1])
        else:
            self.keypair = (key, None)

    def import_public_key(self, key: Union[str, bytes]) -> str:
        key = key if type(key) == str else key.decode('utf-8')
        if self.keypair:
            self.keypair = (self.keypair[0], key)
        else:
            self.keypair = (None, key)
    
    def encrypt(self, plaintext: Union[str, bytes], public_key: Union[str, bytes] = None) -> str:
        public_key = public_key if public_key else self.keypair[1]

        if type(public_key) == str:
            public_key = public_key.encode('utf-8')
        
        key = RSA.import_key(public_key)
        cipher = PKCS1_OAEP.new(key, hashAlgo=SHA256)
        ciphertext = cipher.encrypt(plaintext if type(plaintext) == bytes else plaintext.encode('utf-8'))
        return b64encode(ciphertext).decode('utf-8')
    
    def decrypt(self, ciphertext: str, private_key: Union[str, bytes] = None) -> bytes:
        private_key = private_key if private_key else self.keypair[0]

        if type(private_key) == str:
            private_key = private_key.encode('utf-8')
        
        key = RSA.import_key(private_key)
        cipher = PKCS1_OAEP.new(key, hashAlgo=SHA256)
        plaintext = cipher.decrypt(b64decode(ciphertext))
        return plaintext
    
    def private_key(self) -> str:
        return self.keypair[0]

    def public_key(self) -> str:
        return self.keypair[1]
    
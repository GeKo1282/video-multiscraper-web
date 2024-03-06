from flask import request, jsonify
from scripts.helper.http import Extender

class APIExtender(Extender):
    def __init__(self, socket_host: str, socket_port: int, public_rsa_key: str) -> None:
        self._socket_host: str = socket_host
        self._socket_port: int = socket_port
        self._public_rsa_key: str = public_rsa_key

    def handler(self,):
        if request.method != 'POST':
            return 'Invalid request', 400
        
        data = request.get_json()
        if data.get('action') == "get-websocket-address":
            return self.get_websocket_address()
        
        if data.get('action') == "get-rsa-key":
            return self.get_rsa_key()
        
        return 'Invalid request', 400

    def get_websocket_address(self,):
        return jsonify({
            "address": f"{self._socket_host}:{self._socket_port}"
        })
    
    def get_rsa_key(self,):
        return jsonify({
            "public_rsa_key": self._public_rsa_key or ""
        })
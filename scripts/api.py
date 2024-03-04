from flask import request, jsonify

class Extender:
    def __init__(self, socket_host: str, socket_port: int, public_rsa_key: str) -> None:
        self._socket_host: str = socket_host
        self._socket_port: int = socket_port
        self._public_rsa_key: str = public_rsa_key

    def handler(self,):
        if request.method != 'POST':
            return 'Invalid request', 400
        
        data = request.get_json()
        if data.get('action') == "get-socket-data":
            return self.get_socket_data()
        
        if data.get('action') == "get-public-key":
            return self.get_public_key()

    def get_socket_data(self,):
        return jsonify({
            "socket_host": self._socket_host or "",
            "socket_port": self._socket_port or -1
        })
    
    def get_public_key(self,):
        return jsonify({
            "public_rsa_key": self._public_rsa_key or ""
        })
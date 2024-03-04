import websockets
from websockets.server import (
    serve,
    WebSocketServer as WSServer
)
from websockets.client import WebSocketClientProtocol
import socket, threading, asyncio
from socket import socket as Socket
from typing import Optional

def int_to_bytes(number: int, numbytes: int = 8):
    return number.to_bytes(numbytes, "big")

def bytes_to_int(bytes: bytes):
    return int.from_bytes(bytes, "big")

class SocketServer:
    def __init__(self, host: str = "0.0.0.0", port=5555) -> None:
        self.host: str = host
        self.port: int = port
        self.socket: socket.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    def run(self, handler: callable, as_thread: bool = True) -> Optional[threading.Thread]:
        try:
            self.socket.bind((self.host, self.port))
        except OSError:
            raise AddressAlreadyBoundError(f"Address {self.host}:{self.port} is already in use!")
        
        self.socket.listen(5)
        def inner():
            while True:
                client_socket, client_address = self.socket.accept()
                threading.Thread(target=handler, args=(self, client_socket, client_address)).start()

        if as_thread:
            thread = threading.Thread(target=inner)
            thread.start()
            return thread
        
        inner()

    def send_chunk_size(self, receiver: Socket, chunk_size: int) -> bool:
        return self.send(receiver, int_to_bytes(chunk_size, 8))

    def receive_chunks(self, recv_socket: socket, chunk_size: int) -> bytes:
        final_data = b""
        try:
            data = recv_socket.recv(chunk_size)
            size, data = bytes_to_int(data[:8]), data[8:]
            final_data += data
            for _ in range(0, size - chunk_size, chunk_size):
                final_data += recv_socket.recv(chunk_size)

        except ConnectionResetError:
            return False
        
        return final_data

    def send(self, receiver: Socket, data: bytes, chunk_size: int = None) -> bool:
        data = int_to_bytes(len(data), 8) + data

        if not chunk_size:
            receiver.sendall(data)
            return True
        
        size = len(data)
        for i in range(0, size, chunk_size):
            receiver.sendall(data[i:i+chunk_size])
        return True 

class SocketClient:
    def __init__(self, host: str = "0.0.0.0", port=5555) -> None:
        self.host: str = host
        self.port: int = port
        self.socket: socket.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def connect(self, initial_handler, receive_handler: callable, receive_as_thread: bool = True) -> Optional[threading.Thread]:
        self.socket.connect((self.host, self.port))
        initial_handler(self)
        if receive_as_thread:
            thread = threading.Thread(target=receive_handler, args=(self,))
            thread.start()
            return thread

        receive_handler(self)

    def receive_chunk_size(self) -> int:
        return bytes_to_int(self.socket.recv(8))

    def receive_chunks(self, chunk_size: int) -> bytes:
        final_data = b""
        try:
            data = self.socket.recv(chunk_size)
            size, data = bytes_to_int(data[:8]), data[8:]
            final_data += data
            for _ in range(0, size - chunk_size, chunk_size):
                final_data += self.socket.recv(chunk_size)

        except ConnectionResetError:
            return False
        
        return final_data

    def send(self, data: bytes, chunk_size: int = None) -> bool:
        data = int_to_bytes(len(data), 8) + data

        if not chunk_size:
            self.socket.sendall(data)
            return True
        
        size = len(data)
        for i in range(0, size, chunk_size):
            self.socket.sendall(data[i:i+chunk_size])
        return True

class WebSocketServer:
    def __init__(self, host: str = "0.0.0.0", port: int = 5555) -> None:
        self.host: str = host
        self.port: int = port
        self.socket_server: WSServer = None

    def start(self, handler: callable, as_thread: bool = True) -> Optional[threading.Thread]:        
        async def inner():
            async with serve(host=self.host, port=self.port, ws_handler=handler) as server:
                self.socket_server = server
                await server.wait_closed()
                print("Server closed!")

        if as_thread:
            thread = threading.Thread(target=asyncio.run, args=(inner(),))
            thread.start()
            return thread
        
        asyncio.run(inner())

class AddressAlreadyBoundError(Exception):
    pass

from flask import Flask
from typing import List, Union, Callable, Tuple

class Extender:
    def __init__(self) -> None:
        pass

    def handler(self,):
        print("Handler not implemented")
        # Intended to be overridden by derived classes
        return "", 404

    def register_paths(self) -> List[Tuple[str, List[str], Callable]]:
        # Intended to be overridden by derived classes
        return []

class WebServer:
    def __init__(self) -> None:
        self._app = Flask(__name__)

    def extend(self, extender: Extender) -> None:
        for route, methods, func in extender.register_paths():
            self.add_path(route, methods, func)

    def add_path(self, route: str, methods: List[str], func: Union[Extender, Callable]) -> None:
        self._app.route(route, methods=methods)(func.handler if isinstance(func, Extender) else func)

    def run(self, host: str, port: int) -> None:
        self._app.run(host=host, port=port)
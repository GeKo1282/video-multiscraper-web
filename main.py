import json
from scripts.webserver import WebServer
from scripts.api import Extender as APIExtender

def main():
    SETTINGS = json.load(open("data/settings.json"))

    webserver = WebServer()
    api_extender = APIExtender(socket_host=SETTINGS['socketserver']['host'], socket_port=SETTINGS['socketserver']['port'])
    webserver.add_path("/", ["POST"], api_extender)
    webserver.register_paths()
    webserver.run(SETTINGS['webserver']['host'], SETTINGS['webserver']['port'])

if __name__ == "__main__":
    main()
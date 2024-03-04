async function get_socket_address() {
    let data = await (await fetch('/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            'action': 'get-socket-address'
        })
    })).json();

    address = data['address'];

    if (address.startsWith(":")) {
        address = window.location.hostname + address;
    }

    return address;
}

class WebSocketClient {
    #socket = null;

    #onopen_handler = null;
    #onmessage_handler = null;
    
    #server_rsa_key = null;

    #setup_succeded = {};
    #setup_action_fails = 0;

    #failed_reloads = 0;
    #ready = false;

    constructor(address, rsa_cipher, aes_cipher, failed_reloads = 0) {
        this.address = address;
        this.#failed_reloads = failed_reloads;
        this.rsa_cipher = rsa_cipher;
        this.aes_cipher = aes_cipher;
    }

    set onopen(handler) {
        this.#onopen_handler = handler;
    }

    set onmessage(handler) {
        this.#onmessage_handler = handler;
    }
    
    #request_server_rsa() {
        this.#socket.send(JSON.stringify({
            action: 'get-rsa-key'
        }));
    }
    
    #send_rsa_key() {
        this.#socket.send(JSON.stringify({
            action: 'send-rsa-key',
            key: this.rsa_cipher.public_key[0]
        }));
    }
    
    #send_aes_key() {
        let ciphertext = this.rsa_cipher.encrypt(this.aes_cipher.key, this.#server_rsa_key)

        this.#socket.send(JSON.stringify({
            action: 'send-aes-key',
            key: ciphertext
        }));
    }
    
    #fail_reload() {
        if (this.#setup_action_fails > 5) {
            window.location.href = '/login?failed_reloads=' + (this.#failed_reloads + 1);
        }
    }

    start() {
        if (this.#onmessage_handler == null)
            throw 'onmessage handler must be set!';

        if (!this.#onopen_handler) this.#onopen_handler = () => {};

        this.#socket = new WebSocket('ws://' + this.address);
        this.#socket.onopen = async () => {await this.#setup()};
        this.#socket.onmessage = async (message) => {this.#setup_handler(message)};
    }

    async #setup() {
        this.#request_server_rsa();

        while (!this.#server_rsa_key) {
            await sleep(500);
        }

        this.#send_rsa_key();
        this.#send_aes_key();
    }

    #setup_handler(message) {
        let message_json = JSON.parse(message.data);

        if (message_json.action == 'send-rsa-key') {
            if (!message_json.key) {
                this.#setup_action_fails++;
                this.#fail_reload();
                this.#request_server_rsa();
            }

            this.#server_rsa_key = message_json.key;

            if (global.LOG <= global.LOG_LEVELS.DEBUG) {
                console.log("Received server RSA key!" + global.LOG <= global.LOG_LEVELS.ULTRA_DEBUG? ("The key is: " + this.#server_rsa_key): "");
            }
        }
    
        if (message_json.action == 'receive-rsa-key') {
            if (!message_json.success) {
                this.#setup_action_fails++;
                this.#fail_reload();
                this.#send_rsa_key();
            }

            this.#setup_succeded['send-rsa-public-key'] = true;

            if (global.LOG <= global.LOG_LEVELS.DEBUG) {
                console.log('Server has successfully received RSA public key.');
            }
        }
        
        if (message_json.action == 'receive-aes-key') {
            if (!message_json.success) {
                this.#setup_action_fails++;
                this.#fail_reload();
                this.#send_aes_key();
            }

            this.#setup_succeded['send-aes-key'] = true;

            if (global.LOG <= global.LOG_LEVELS.DEBUG) {
                console.log('Server has successfully received AES key.');
            }
        }

        if (this.#setup_succeded['send-rsa-public-key'] && this.#setup_succeded['send-aes-key'] && this.#server_rsa_key) {
            if (global.LOG <= global.LOG_LEVELS.DEV_INFO) {
                console.log('Setup completed successfully!');
            }
            
            this.#ready = true;

            this.#socket.onmessage = (message) => {this.#regular_handler(message)};
            this.#onopen_handler();
        }
    }

    #regular_handler(message) {
        let iv = this.rsa_cipher.decrypt(message.data.substring(0, 344));
        let data = message.data.substring(344);
        
        let decrypted = this.aes_cipher.decrypt(data, this.aes_cipher.key, iv);
        this.#onmessage_handler(decrypted, message);
    }

    send(data) {
        let [encrypted, iv] = this.aes_cipher.encrypt(data);
        iv = this.rsa_cipher.encrypt(iv, this.#server_rsa_key);

        if (global.LOG <= global.LOG_LEVELS.ULTRA_DEBUG) {
            console.log('Sending message:\n', {iv: iv, data: encrypted, iv_length: iv.length, data_length: encrypted.length, original_message: data});
        }

        this.#socket.send(iv + encrypted); //IV should always be 344 bytes long (as it is base64 encoded + rsa encrypted)
    }

    get ready() {
        return this.#ready;
    }
}
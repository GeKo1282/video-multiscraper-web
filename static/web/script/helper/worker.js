window = self
importScripts("./forge.min.js", "./rsa.js");

this.addEventListener('message', function(event) {
    if (event.data.action == 'generate-rsa-keypair') {
        let cipher = new RSACipher(false);
        cipher.generate_keys(event.data.key_length);
        this.postMessage({
            message: 'rsa-keypair',
            data: {
                public_key: cipher.public_key[0],
                private_key: cipher.private_key,
                max_length: cipher.max_message_length
            }
        });
    }
}, false);
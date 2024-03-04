class AESCipher {
    #key = null;
    
    constructor(key_bits = 256) {
        if (key_bits == false) {
            this.#key = null;
        }

        if (key_bits > 0) {
            try {
                this.#key = this.generate_key(key_bits / 8);
            } catch (e) {
                throw "Key length must be power of two between 128 and 256!"
            }
        }
    }

    generate_key(key_bytes) {
        if (Math.log2(key_bytes) % 1 !== 0 || key_bytes < 16 || key_bytes > 32) {
            throw "Key length must be power of two between 16 and 32!";
        }

        return forge.util.encode64(forge.random.getBytesSync(key_bytes));
    }

    encrypt(text, base64_key) {
        let key = forge.util.decode64(base64_key || this.#key);

        let iv = forge.random.getBytesSync(16);
        let cipher = forge.cipher.createCipher('AES-CBC', key);

        cipher.start({iv: iv});
        cipher.update(forge.util.createBuffer(text));
        cipher.finish();

        let encrypted = cipher.output.getBytes();

        return [forge.util.encode64(encrypted), forge.util.encode64(iv)];
    }

    decrypt(base64_ciphertext, base64_key, base64_iv) {
        let key = forge.util.decode64(base64_key || this.#key);
        let iv = forge.util.decode64(base64_iv);
        let ciphertext = forge.util.decode64(base64_ciphertext);

        let decipher = forge.cipher.createDecipher('AES-CBC', key);

        decipher.start({iv: iv});
        decipher.update(forge.util.createBuffer(ciphertext));
        decipher.finish();

        return decipher.output.toString();
    }

    encrypt_ecb(text, base64_key) {
        let key = forge.util.decode64(base64_key || this.#key);

        let cipher = forge.cipher.createCipher('AES-ECB', key);

        cipher.start();
        cipher.update(forge.util.createBuffer(text));
        cipher.finish();

        let encrypted = cipher.output.getBytes();

        return forge.util.encode64(encrypted);
    }

    decrypt_ecb(base64_ciphertext, base64_key) {
        let key = forge.util.decode64(base64_key || this.#key);
        let ciphertext = forge.util.decode64(base64_ciphertext);

        let decipher = forge.cipher.createDecipher('AES-ECB', key);

        decipher.start();
        decipher.update(forge.util.createBuffer(ciphertext));
        decipher.finish();

        return decipher.output.toString();
    }

    get key() {
        return this.#key;
    }

    set key(key) {
        this.#key = key;
    }
}
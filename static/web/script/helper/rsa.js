const rsa = forge.pki.rsa;

class RSACipher {
    #keypair;
    #max_length;
    #default_public_key;
    #default_private_key;

    constructor(generate_keys = true) {
        this.#keypair = {};
        if (generate_keys) {
            this.generate_keys();
        }
    }

    static #import_public_key (key) {
        if (!key) return null;
        if (typeof key !== "string") return key;
        try {
            return forge.pki.publicKeyFromPem(key);
        } catch (e) {
            throw "Invalid PEM key!";
        }
    }

    static #import_private_key (key) {
        if (!key) return null;
        if (typeof key !== "string") return key;
        try {
            return forge.pki.privateKeyFromPem(key);
        } catch (e) {
            throw "Invalid PEM key!";
        }
    }

    static #_encrypt(key, text) {
        let RSACiphertext = key.encrypt(text, 'RSA-OAEP', {
            md: forge.md.sha256.create()
        });
        return forge.util.encode64(RSACiphertext);
    }

    static #_decrypt(key, encoded) {
        return key.decrypt(forge.util.decode64(encoded), 'RSA-OAEP', {
            md: forge.md.sha256.create()
        });
    }

    set_default_keys(private_key = null, public_key = null) {
        if (private_key) this.#default_private_key = RSACipher.#import_private_key(private_key, this.#default_private_key);
        if (public_key) this.#default_public_key = RSACipher.#import_public_key(public_key, this.#default_public_key);
    } 

    import_public_key(key, max_message_length) {
        this.#keypair.publicKey = forge.pki.publicKeyFromPem(key);
        this.#max_length = max_message_length;
        if (!this.#default_public_key) {
            this.set_default_keys(null, this.#keypair.publicKey);
        }
    }

    import_private_key(key) {
        this.#keypair.privateKey = forge.pki.privateKeyFromPem(key);
        if (!this.#default_private_key) {
            this.set_default_keys(this.#keypair.privateKey, null);
        }
    }

    get public_key() {
        return [forge.pki.publicKeyToPem(this.#keypair.publicKey), this.#max_length];
    }

    get private_key() {
        return forge.pki.privateKeyToPem(this.#keypair.privateKey);
    }

    get max_message_length() {
        return this.#max_length;
    }

    generate_keys(length = 2048) {
        if (Math.log2(length) % 1 !== 0 || length < 512 || length > 4096) {
            throw "Key length must be power of two between 512 and 4096!";
        }
        this.#keypair = rsa.generateKeyPair({bits: length, workers: -1});
        this.#default_public_key ??= this.#keypair.publicKey;
        this.#default_private_key ??= this.#keypair.privateKey;
        this.#max_length = length / 8 - (2 * 256 / 8) - 2;
    }

    static static_encrypt(text, key) {
        key = RSACipher.#import_public_key(key, null);
        text = forge.util.encodeUtf8(text);
        
        return RSACipher.#_encrypt(key, text);
    }

    encrypt(text, key = null) {
        key = RSACipher.#import_public_key(key || this.#default_public_key || null);
        if (!key) throw 'Keys are not set, neither key was provided to function or it was incorrect!';

        return RSACipher.#_encrypt(key, forge.util.encodeUtf8(text));
    }

    decrypt(text, key = null) {
        key = RSACipher.#import_private_key(key || this.#default_private_key || null);
        if (!key) throw 'Keys are not set, neither key was provided to function or it was incorrect!';
 
        return forge.util.decodeUtf8(RSACipher.#_decrypt(key, text));
    }
}
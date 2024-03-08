if (!window.global) 
    window.global = {};

global = window.global;

addLoadEvent(() => {
    // Generate RSA keypair

    const worker = new Worker('./script/helper/worker.js');
    
    worker.onmessage = (e) => {
        if (e.data.message == 'rsa-keypair') {
            global.rsa = new RSACipher();
            global.rsa.import_public_key(e.data.data.public_key, e.data.data.max_length);
            global.rsa.import_private_key(e.data.data.private_key);
        }
    }

    worker.postMessage({
        action: 'generate-rsa-keypair',
        key_length: 2048
    });
});

addLoadEvent(async () => {
    // Get data about and connect to socket
    await initialize_websocket_communications((decrypted, message) => {
        console.log(decrypted);
        console.log(message);
    });

    global.websocket.send('test');
});

function login() {
    var username = document.getElementById('login-username-input').value;
    var password = document.getElementById('login-username-password').value;
    var data = {
        username: username,
        password: password
    };
}
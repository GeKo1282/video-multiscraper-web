if (!window.global) 
    window.global = {};

global = window.global;

addLoadEvent(() => {
    let username = (new URLSearchParams(window.location.search)).get('username');

    if (username) {
        document.getElementById('login-username-input').value = atob(username);
        if (document.getElementById('login-password-input').oninput) document.getElementById('login-password-input').oninput();
    }
});

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
    await initialize_websocket_communications((decrypted, _message_object) => {
        decrypted = JSON.parse(decrypted);

        if (decrypted.action == 'login') {
            if (decrypted.success) {
                sessionStorage.setItem('token', decrypted.data.token);
                window.location.href = '/';
            } else {
                alert('Invalid username or password');
            }
        }

        console.log(decrypted);
    });
});

async function login() {
    let username = document.getElementById('login-username-input').value;
    let password = document.getElementById('login-password-input').value;

    
    let md = forge.md.sha512.create();
    md.update(password);
    let password_hash = md.digest().toHex();

    while (!global.websocket.ready) {
        await sleep(50);
    }

    global.websocket.send(JSON.stringify({
        action: 'login',
        data: {
            username: username,
            password: password_hash
        }
    }));
}
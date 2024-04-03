if (!window.global) 
    window.global = {};

global = window.global;

global.requirements = {
    "req-8": (value) => {
        return value.length >= 8;
    },
    "req-max-64": (value) => {
        return value.length <= 64;
    },
    "req-num": (value) => {
        return value.match(/[0-9]/);
    },
    "req-upper": (value) => {
        return value.match(/[A-Z]/);
    },
    "req-lower": (value) => {
        return value.match(/[a-z]/);
    },
    "req-special": (value) => {
        return value.match(/[_\!\@\#\$\%\^\&\*\(\)-+=\[\]{}\|;:,.<>\?]/);
    },
    "req-chars": (value) => {
        return value.match(/^[A-Za-z0-9_\!\@\#\$\%\^\&\*\(\)-+=\[\]{}\|;:,.<>\?]+$/);
    }
}

addLoadEvent(() => {
    if (localStorage.getItem('token') && localStorage.getItem('user_id')) {
        window.location.href = '/';
    }
});

addLoadEvent(() => {
    let username = (new URLSearchParams(window.location.search)).get('username');

    if (username) {
        document.getElementById('login-username-input').value = atob(username);
        if (document.getElementById('login-password-input').oninput) document.getElementById('login-password-input').oninput();
    }
});

addLoadEvent(() => {
    // Assign events to password validators on register page
    let password_input = document.getElementById('register-password-input');

    let oldoninput = password_input.oninput;

    password_input.oninput = () => {
        if (oldoninput) oldoninput();

        let password = password_input.value;
    
        for (let req of Object.keys(global.requirements)) {
            if (global.requirements[req](password)) {
                document.getElementById("password-requirements").getElementsByClassName(req)[0].classList.add('fulfilled');
            } else {
                document.getElementById("password-requirements").getElementsByClassName(req)[0].classList.remove('fulfilled');
            }
        }
    }
})

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
    global.socket_hander = (decrypted, _message_object) => {
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
    }

    // Get data about and connect to socket
    await initialize_websocket_communications(global.socket_hander);
});

async function login() {
    let username = document.getElementById('login-username-input').value;
    let password = document.getElementById('login-password-input').value;

    while (!global.websocket.ready || !global.websocket.full_encryption) {
        await sleep(50);
    }

    global.websocket.onmessage = (decrypted, _) => {
        decrypted = JSON.parse(decrypted);
        if (decrypted.action != 'get-salt' || !decrypted.success) {
            global.socket_hander(decrypted, _);
            return;
        }

        global.websocket.onmessage = (decrypted, _) => {
            decrypted = JSON.parse(decrypted);
            if (decrypted.action != 'send-user-auth' || !decrypted.success) {
                global.socket_hander(decrypted, _);
                return;
            }
    
            global.websocket.onmessage = global.socket_hander;
    
            localStorage.setItem('token', decrypted.data.token);
            localStorage.setItem('user_id', decrypted.data.id);

            window.location.href = '/';
        };

        global.websocket.send(JSON.stringify({
            action: 'get-user-auth',
            data: {
                username: username,
                password: sha512(password, decrypted.data.salt)
            }
        }));
    }

    global.websocket.send(JSON.stringify({
        action: 'get-salt',
        data: {
            username: username
        }
    }));
}

async function register() {
    let salt = generate_string(32);

    let data = {
        username: document.getElementById('register-username-input').value,
        displayname: document.getElementById('register-displayname-input').value,
        email: document.getElementById('register-email-input').value,
        password: sha512(document.getElementById('register-password-input').value, salt),
        salt: salt
    };

    if (document.getElementById('register-password-input').value != document.getElementById('register-password-repeat-input').value) {
        document.getElementById('register-password-input').value = '';
        document.getElementById('register-password-repeat-input').value = '';
        document.getElementById('register-password-input').oninput();
        return;
    }

    while (!global.websocket.ready || !global.websocket.full_encryption) {
        await sleep(50);
    }

    global.websocket.onmessage = (decrypted, _) => {
        decrypted = JSON.parse(decrypted);
        if (decrypted.action != 'send-user-auth' || !decrypted.success) {
            global.socket_hander(decrypted, _);
            return;
        }

        global.websocket.onmessage = global.socket_hander;

        localStorage.setItem('token', decrypted.data.token);
        localStorage.setItem('user_id', decrypted.data.user_id);
    };

    global.websocket.send(JSON.stringify({
        action: 'register',
        data: data
    }));
}
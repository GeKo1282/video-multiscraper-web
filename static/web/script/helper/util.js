if (!window.global) window.global = {};
global = window.global;

global.LOG_LEVELS = {
    ULTRA_DEBUG: -1,
    DEBUG: 0,
    INFO: 10,
    WARNING: 20,
    ERROR: 30,
    CRITICAL: 40
}

global.LOG = global.LOG_LEVELS.DEBUG;

global.standard_validators = {
    'username': (value) => {
        for (let character of value) {
            if (!'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.'.includes(character)) return false;
        }

        return value.length >= 4 && value.length <= 64;
    },
    'email': (value) => {
        return RegExp("[-A-Za-z0-9!#$%&'*+/=?^_`{|}~]+(?:\.[-A-Za-z0-9!#$%&'*+/=?^_`{|}~]+)*@(?:[A-Za-z0-9](?:[-A-Za-z0-9]*[A-Za-z0-9])?\.)+[A-Za-z0-9](?:[-A-Za-z0-9]*[A-Za-z0-9])?").test(value);
    },
    'password': (value) => {
        for (let character of value) {
            if (!'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_!@#$%^&*()-+=[]{}|;:,.<>?'.includes(character)) return false;
        }

        return value.length >= 8 && value.length <= 64;
    },
    'password-create': (value) => {
        let checks = [value.length >= 8, value.length <= 64,
        any(Array.from(value).map((character) => character.match(/[0-9]/))),
        any(Array.from(value).map((character) => character.match(/[A-Z]/))),
        any(Array.from(value).map((character) => character.match(/[a-z]/))),
        Boolean(value.match(/^[A-Za-z0-9_\!\@\#\$\%\^\&\*\(\)-+=\[\]{}\|;:,.<>\?]+$/))];
        return all(checks);
    },
    'displayname': (value) => {
        return value.length >= 4 && value.length <= 64;
    }
}

global.icons = {
    x: {
        type: "svg",
        path: [
            ["M4.646 4.646a.5.5 0 0 1 .708 0L8 7.293l2.646-2.647a.5.5 0 0 1 .708.708L8.707 8l2.647 2.646a.5.5 0 0 1-.708.708L8 8.707l-2.646 2.647a.5.5 0 0 1-.708-.708L7.293 8 4.646 5.354a.5.5 0 0 1 0-.708"],
        ]
    },
    check: {
        type: "svg",
        path: [
            ["M10.97 4.97a.75.75 0 0 1 1.07 1.05l-3.99 4.99a.75.75 0 0 1-1.08.02L4.324 8.384a.75.75 0 1 1 1.06-1.06l2.094 2.093 3.473-4.425z"]
        ]
    },
    question: {
        type: "svg",
        path: [
            ["M5.255 5.786a.237.237 0 0 0 .241.247h.825c.138 0 .248-.113.266-.25.09-.656.54-1.134 1.342-1.134.686 0 1.314.343 1.314 1.168 0 .635-.374.927-.965 1.371-.673.489-1.206 1.06-1.168 1.987l.003.217a.25.25 0 0 0 .25.246h.811a.25.25 0 0 0 .25-.25v-.105c0-.718.273-.927 1.01-1.486.609-.463 1.244-.977 1.244-2.056 0-1.511-1.276-2.241-2.673-2.241-1.267 0-2.655.59-2.75 2.286m1.557 5.763c0 .533.425.927 1.01.927.609 0 1.028-.394 1.028-.927 0-.552-.42-.94-1.029-.94-.584 0-1.009.388-1.009.94"]
        ]
    },
    search: {
        type: "svg",
        path: [
            "M11.742 10.344a6.5 6.5 0 1 0-1.397 1.398h-.001q.044.06.098.115l3.85 3.85a1 1 0 0 0 1.415-1.414l-3.85-3.85a1 1 0 0 0-.115-.1zM12 6.5a5.5 5.5 0 1 1-11 0 5.5 5.5 0 0 1 11 0"
        ]
    },
    more: {
        type: "svg",
        path: [
            "M3 9.5a1.5 1.5 0 1 1 0-3 1.5 1.5 0 0 1 0 3m5 0a1.5 1.5 0 1 1 0-3 1.5 1.5 0 0 1 0 3m5 0a1.5 1.5 0 1 1 0-3 1.5 1.5 0 0 1 0 3"
        ]
    }
}

const sleep = ms => new Promise(r => setTimeout(r, ms));

function addLoadEvent(func) {
    let oldonload = window.onload;
	if (typeof window.onload != 'function') {
		window.onload = func;
	} else {
		window.onload = function() {
			if (oldonload) {
			    try {
			        oldonload();
                } catch (e) {console.log("%c" + e.stack, "color: red;");}

			}

			try {
			    func();
			} catch (e) {console.log("%c" + e.stack, "color: red;");}

		}
	}
}

function make_validator(object, validator_function) {
    old_onkeup = object.onkeyup;

    object.onkeyup = () => {
        if (validator_function(object.value)) {
            object.classList.remove('invalid');
            object.classList.add('valid');
        } else {
            object.classList.remove('valid');
            object.classList.add('invalid');
        }

        if (old_onkeup) old_onkeup();
    }
}

function make_validator_function(type, data) {
    if (type == 'standard') {
        if (data.includes('&')) {
            let validators = data.split('&');
            return (value) => {
                for (let validator of validators) {
                    if (!global.standard_validators[validator](value)) return false;
                }
                return true;
            }
        }

        if (data.includes('|')) {
            let validators = data.split('|');
            return (value) => {
                for (let validator of validators) {
                    if (global.standard_validators[validator](value)) return true;
                }
                return false;
            }
        }

        return (value) => {
            return global.standard_validators[data](value);
        }
    } else if (type == 'regex') {
        return (value) => {
            return RegExp(data).test(value);
        }
    } else if (type == 'custom') {
        return (value) => {
            if (Object.keys(data).includes('length')) {
                if (Object.keys(data.length).includes('min')) {
                    if (value.length < data.length.min) return false;
                }

                if (Object.keys(data.length).includes('max')) {
                    if (value.length > data.length.max) return false;
                }
            }

            if (Object.keys(data).includes('regex')) {
                if (!RegExp(data.regex).test(value)) return false;
            }

            if (Object.keys(data).includes('characters')) {
                for (let character of data.characters) {
                    if (!value.includes(character)) return false;
                }
            }

            return true;
        }
    };
}

async function initialize_websocket_communications(regular_handler) {
    let continue_setup = false;

    if (!global.rsa) {
        const worker = new Worker('./script/helper/worker.js');

        worker.onmessage = (e) => {
            if (e.data.message == 'rsa-keypair') {
                global.rsa = new RSACipher(false);
                global.rsa.import_public_key(e.data.data.public_key, e.data.data.max_length);
                global.rsa.import_private_key(e.data.data.private_key);
                continue_setup = true;
            }
        }

        worker.postMessage({'action': 'generate-rsa-keypair'});
    } else {
        continue_setup = true;
    }

    if (!global.aes) {
        global.aes = new AESCipher();
        global.aes.generate_key(32);
    }

    while (!continue_setup) {
        await sleep(50);
    }

    if (!global.websocket) {
        let websocket_address = await get_socket_address();

        global.websocket = new WebSocketClient(websocket_address, global.rsa, global.aes);

        global.websocket.add_onmessage(regular_handler);

        global.websocket.start();
    }

    while (!global.websocket.ready) {
        await sleep(50);
    }
}

function make_icon(element) {
    let icon_name = element.dataset.icon;

    if (!Object.keys(global.icons).includes(icon_name)) {
        return element;
    }

    if (global.icons[icon_name].type == "svg") {
        let svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");

        svg.setAttribute('viewBox', '0 0 16 16');
        svg.setAttribute('xmlns', 'http://www.w3.org/2000/svg');

        for (let path of global.icons[icon_name].path) {
            let path_element = document.createElementNS("http://www.w3.org/2000/svg", "path");
            path_element.setAttribute('d', path);
            path_element.setAttribute('xmlns', 'http://www.w3.org/2000/svg');
            svg.appendChild(path_element);
        }

        element.appendChild(svg);
    }

    return element;
}

function place_icons() {
    let icons = document.getElementsByClassName('icon');
    for (let icon of icons) {
        icon.outerHTML = make_icon(icon).outerHTML;
    }
}

function any(iterable) {
    for (let element of iterable) {
        if (element) return true;
    }
    return false;
}

function all(iterable) {
    for (let element of iterable) {
        if (!element) return false;
    }
    return true;
}

function sha512(string, salt) {
    let hash = forge.md.sha512.create();
    if (salt) hash.update(salt);
    hash.update(string);
    return hash.digest().toHex();
}

function generate_string(length) {
    let result = '';
    let characters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
    for (let i = 0; i < length; i++) {
        result += characters.charAt(Math.floor(Math.random() * characters.length));
    }
    return result;
}

addLoadEvent(() => {
    place_icons();
});
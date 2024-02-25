if (!window.global) window.global = {};
global = window.global;

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
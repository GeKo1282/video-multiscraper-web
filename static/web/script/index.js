global.default_socket_hander = (decrypted, _) => {
    if (decrypted.action == "send-search-suggestions") {
        if (!global.search_suggestions_cache) global.search_suggestions_cache = {};

        global.search_suggestions_cache[decrypted.data.query] = decrypted.data.suggestions;
        update_search_suggestions(decrypted.data.suggestions);
        return;
    }

    console.log(decrypted);
}

global.user_info_updaters = {
    "displayname": ['#user-profile-box .profile-name'],
    "avatar": [() => {
        document.getElementById('user-profile-box').getElementsByClassName('profile-image')[0].setAttribute('style', '--image-url: url(' + global.user.info.avatar_url + ');');
    }]
}

addLoadEvent(async () => {
    if (!localStorage.getItem('token') || !localStorage.getItem('user_id')) {
        window.location.href = '/login';
    }
})

addLoadEvent(async () => {
    if (!global.user) global.user = {};
    if (!global.user.info) global.user.info = {};
    global.user.info.id = localStorage.getItem('user_id');
    global.user.info.token = localStorage.getItem('token');

    await initialize_websocket_communications(global.default_socket_hander);
    await get_user_info();
    update_user_info();
    assign_clicks();
    assign_handlers();
})

async function get_user_info() {
    let promise = new Promise((resolve, reject) => {
        global.websocket.onmessage = (decrypted, _) => {
            if (decrypted.action != 'send-user-info' || !decrypted.success) {
                global.default_socket_hander(decrypted, _);
                return;
            }
            
            if (!global.user) global.user = {};
            if (!global.user.info) global.user.info = {};

            global.user.info.username = decrypted.data.username;
            global.user.info.displayname = decrypted.data.displayname;
            global.user.info.email = decrypted.data.email;
            global.user.info.avatar_url = decrypted.data.avatar;
            global.user.info.created_at = decrypted.data.created_at;

            resolve();
        }
    });

    global.websocket.send(JSON.stringify({
        action: 'get-user-info',
        data: {
            id: global.user.info.id,
            token: global.user.info.token
        }
    }));

    await promise;
}

function update_user_info() {
    for (let key of Object.keys(global.user_info_updaters)) {
        for (let element of global.user_info_updaters[key]) {
            if (typeof element == 'string') {
                document.querySelector(element).innerText = global.user.info[key];
            } else {
                element();
            }
        }
    }
}

function assign_clicks() {
    let events = {
        '#user-profile-box': {
            'click': switch_user_menu
        }
    }

    for (let selector of Object.keys(events)) {
        for (let event of Object.keys(events[selector])) {
            document.querySelector(selector).addEventListener(event, events[selector][event]);
        }
    }
}

function assign_handlers() {
    document.getElementById('search-bar').getElementsByClassName('search-input')[0].addEventListener('keyup', get_search_suggestions);
    document.getElementById('search-bar').getElementsByClassName('search-input')[0].addEventListener('keydown', async (event) => {
        if (event.key == 'Enter') {
            let value = document.getElementById('search-bar').getElementsByClassName('search-input')[0].value;
            switch_window('search');
            await websocket.send(JSON.stringify({
                action: 'search',
                data: {
                    query: value,
                    limit: 20,
                    start: 0,
                    provider: 'all',
                    categorize: 'stored+mixed+providers'
                }
            }));
        }
    });
}

async function get_search_suggestions() {
    let value = document.getElementById('search-bar').getElementsByClassName('search-input')[0].value;

    if (value.length == 0) {
        update_search_suggestions([]);
        return;
    }

    if (global.search_suggestions_cache && global.search_suggestions_cache[value]) {
        update_search_suggestions(global.search_suggestions_cache[value]);
        return;
    }

    await global.websocket.send(JSON.stringify({
        action: 'get-search-suggestions',
        data: {
            query: value
        }
    }));
}

function logout() {
    localStorage.removeItem('token');
}

function hide_user_menu() {
    document.getElementById('user-profile-box').getElementsByClassName('profile-scrolldown')[0].classList.remove('shown');
}

function show_user_menu() {
    document.getElementById('user-profile-box').getElementsByClassName('profile-scrolldown')[0].classList.add('shown');
}

function switch_user_menu() {
    if (document.getElementById('user-profile-box').getElementsByClassName('profile-scrolldown')[0].classList.contains('shown')) {
        hide_user_menu();
    } else {
        show_user_menu();
    }
}

function update_search_suggestions(suggestions) {
    let suggestions_box = document.getElementById('search-bar').getElementsByClassName('search-suggestions')[0];
    suggestions_box.innerHTML = '';

    for (let suggestion of suggestions) {
        let suggestion_element = document.createElement('div');
        suggestion_element.classList.add('suggestion');
        suggestion_element.innerText = suggestion;
        suggestion_element.addEventListener('click', () => {
            document.getElementById('search-bar').getElementsByClassName('search-input')[0].value = suggestion;
            update_search_suggestions([]);
        });
        suggestions_box.appendChild(suggestion_element);
    }
}

function switch_window(partial_id) {
    if (!partial_id.endsWith('-window')) partial_id += '-window';

    let all_windows = document.getElementById('app-layer').getElementsByClassName('window');

    all_windows.filter(window => window.id != partial_id).forEach(window => {
        window.classList.remove('shown');
    });

    document.getElementById(partial_id).classList.add('shown');
}
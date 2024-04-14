global.default_socket_hander = (decrypted, _) => {
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

function switch_page(page_id) {
    if (!page_id.endsWith('-page')) page_id += '-page';

    let pages = [...Array.from(document.getElementById("app-layer").getElementsByClassName('page shown')),
    ...Array.from(document.getElementById("floating-layer").getElementsByClassName('page shown'))];

    pages.forEach((element) => {
        element.classList.remove('shown');
    });

    document.getElementById(page_id).classList.add('shown');
}

async function get_user_info() {
    let promise = new Promise((resolve, reject) => {
        global.websocket.add_onmessage((decrypted, _, self) => {
            if (decrypted.action != 'send-user-info' || !decrypted.success) {
                global.websocket.pass_onmessage(self, decrypted, _);
                return;
            }
            
            if (!global.user) global.user = {};
            if (!global.user.info) global.user.info = {};

            global.user.info.username = decrypted.data.username;
            global.user.info.displayname = decrypted.data.displayname;
            global.user.info.email = decrypted.data.email;
            global.user.info.avatar_url = decrypted.data.avatar;
            global.user.info.created_at = decrypted.data.created_at;

            global.websocket.remove_onmessage(self);

            resolve();
        });
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
            event.preventDefault();
            update_search_suggestions([]);
            if (document.activeElement == document.getElementById('search-bar').getElementsByClassName('search-input')[0]) document.activeElement.blur();
            await search();
        }

        if (event.key == 'ArrowDown' || event.key == 'ArrowUp') {
            event.preventDefault();
            let suggestions = document.getElementById('search-bar').getElementsByClassName('search-suggestions')[0].getElementsByClassName('suggestion');
            if (suggestions.length == 0) return;

            let search_input = document.getElementById('search-bar').getElementsByClassName('search-input')[0];
            let selected = document.getElementById('search-bar').getElementsByClassName('search-suggestions')[0].getElementsByClassName('selected')[0];
            
            let index = selected ?  Array.from(suggestions).indexOf(selected) : (event.key == 'ArrowDown' ? suggestions.length + 2 : -2);
            if (event.key == 'ArrowDown') {
                index++;
            } else {
                index--;
            }

            if (index < 0) index = suggestions.length - 1;
            if (index >= suggestions.length) index = 0;

            for (let suggestion of suggestions) {
                suggestion.classList.remove('selected');
            }

            suggestions[index].classList.add('selected');
            search_input.value = suggestions[index].innerText;
        }
    });
}

async function search() {
    let value = document.getElementById('search-bar').getElementsByClassName('search-input')[0].value;

    global.websocket.add_onmessage((decrypted, _, self) => {
        if (decrypted.action != 'search-results') global.websocket.pass_onmessage(self, decrypted, _);
        

        console.log(decrypted);
        update_search_results(decrypted.data);
        switch_page('search-results');
        global.websocket.remove_onmessage(self);
    });
    
    await global.websocket.send(JSON.stringify({
        action: 'search',
        data: {
            query: value,
            user_id: global.user.info.id,
            token: global.user.info.token
        }
    }));
}

async function get_search_suggestions(event) {
    let value = document.getElementById('search-bar').getElementsByClassName('search-input')[0].value;

    if (value.length == 0) {
        update_search_suggestions([]);
        return;
    }

    if(event.key == 'Enter') return;
    if (event.key == 'ArrowDown' || event.key == 'ArrowUp') return;
    if (event.key == 'Escape') {
        update_search_suggestions([]);
        return;
    }

    if (global.search_suggestions_cache && global.search_suggestions_cache[value]) {
        update_search_suggestions(global.search_suggestions_cache[value]);
        return;
    }

    global.websocket.add_onmessage((decrypted, _, self) => {
        if (decrypted.action != 'send-search-suggestions') global.websocket.pass_onmessage(self, decrypted, _);

        if (!global.search_suggestions_cache) global.search_suggestions_cache = {};

        global.search_suggestions_cache[decrypted.data.query] = decrypted.data.suggestions;
        update_search_suggestions(decrypted.data.suggestions);
        global.websocket.remove_onmessage(self);
        return;
    });

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
            search();
        });
        suggestions_box.appendChild(suggestion_element);
    }
}

function update_search_results(results_json) {
    let results_box = document.getElementById('search-results');
    results_box.innerHTML = '';

    let header = document.createElement('div');
    header.classList.add('header');
    header.innerText = 'Search Results For: ' + results_json.query;

    results_box.appendChild(header);

    for (let result of results_json.results) {
        let result_element = document.createElement('div');
        
        let tooltip = document.createElement('div');
        let tooltip_icon = document.createElement('div');

        let thumbnail = document.createElement('img');
        let details = document.createElement('div');

        let title = document.createElement('div');
        let description = document.createElement('div');
        
        thumbnail.classList.add('thumbnail');
        details.classList.add('details');
        title.classList.add('title');
        description.classList.add('description');
        result_element.classList.add('result');
        tooltip.classList.add('tooltip');
        tooltip_icon.classList.add('tooltip-icon');

        tooltip_icon.setAttribute('data-icon', 'more');

        tooltip_icon = make_icon(tooltip_icon);

        thumbnail.src = result.thumbnail;

        title.innerText = result.title;
        description.innerText = result.description;

        result_element.addEventListener('click', () => {
            open_content_page(result.uid);
        });

        details.appendChild(title);
        details.appendChild(description);
        tooltip.appendChild(tooltip_icon);

        result_element.appendChild(thumbnail);
        result_element.appendChild(details);
        result_element.appendChild(tooltip);

        results_box.appendChild(result_element);
    }
}

async function open_content_page(content_uid) {
    let elements = {
        page: document.getElementById('content-page'),

        title: document.getElementById('content-page').getElementsByClassName('title')[0],
        image: document.getElementById('content-page').getElementsByClassName('image')[0],
        controls: document.getElementById('content-page').getElementsByClassName('controls')[0],

        description: document.getElementById('content-page').getElementsByClassName('description')[0],
        tags: document.getElementById('content-page').getElementsByClassName('tags')[0],

        trailer: document.getElementById('content-page').getElementsByClassName('trailer')[0],
        episodes: document.getElementById('content-page').getElementsByClassName('episodes')[0],
        sources: document.getElementById('content-page').getElementsByClassName('sources')[0]
    }

    let get_data = new Promise((resolve, reject) => {
        global.websocket.add_onmessage((decrypted, _, self) => {
            if (decrypted.action != 'send-content-info') {
                global.websocket.pass_onmessage(self, decrypted, _);
                return;
            }

            global.websocket.remove_onmessage(self);
            resolve(decrypted.data);
        })

        global.websocket.send(JSON.stringify({
            action: 'get-content-info',
            data: {
                content_uid: content_uid,
                user_id: global.user.info.id,
                token: global.user.info.token
            }
        }));
    })

    let page_data = await get_data;

    console.log(page_data);
}
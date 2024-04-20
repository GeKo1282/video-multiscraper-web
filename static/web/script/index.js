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

    assign_handlers();
    make_sliders();
    await initialize_websocket_communications(global.default_socket_hander);
    await get_user_info();
    parse_urlargs();
})

function parse_urlargs() {
    let url = new URL(window.location.href);
    let path = url.pathname;
    let args = url.searchParams;

    let pathlist = {
        "/search": (args) => {
            let query = args.get('query');
            if (!query) return;
            
            query = atob(query);

            document.getElementById('search-bar').getElementsByClassName('search-input')[0].value = query;
            search();
        },
        "/content": (args) => {
            let uid = args.get('uid');
            if (!uid) return;

            uid = atob(uid);

            open_content_page(uid);
        }
    }

    if (pathlist[path]) pathlist[path](args);
}

function make_sliders() {
    let sliders = document.getElementsByClassName('custom-slider');

    for (let slider of sliders) {
        let choices = slider.getElementsByClassName('choice');
        
        for (let choice of choices) {
            choice.addEventListener('click', () => {
                slider.setAttribute('style', '--slider-position: ' + (Array.from(choices).indexOf(choice) + 1) + ';');

                for (let choice of choices) {
                    choice.classList.remove('selected');
                }

                choice.classList.add('selected');

                if (choice.hasAttribute('data-callback')) {
                    eval(choice.getAttribute('data-callback'));
                }
            });
        }
    }
}

function switch_page(page_id, change_url = true, clear_favicon = true) {
    if (!page_id.endsWith('-page')) page_id += '-page';

    let target = document.getElementById(page_id);

    let pages = [...Array.from(document.getElementById("app-layer").getElementsByClassName('page shown')),
    ...Array.from(document.getElementById("floating-layer").getElementsByClassName('page shown'))];

    pages.forEach((element) => {
        element.classList.remove('shown');
    });

    target.classList.add('shown');

    if (change_url) window.history.pushState({id: "100"}, target.id, target.dataset.path ? target.dataset.path : '/' + target.id.replace('-page', ''));
    if (clear_favicon) changeFavicon('/media/favicon.ico');
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
    update_user_info();
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

function assign_handlers() {
    document.getElementById('user-profile-box').onclick = (event) => {
        if (document.getElementById('user-profile-box').getElementsByClassName('profile-scrolldown')[0].contains(event.target)) return;
        switch_user_menu();
    }
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

    let url = new URL(window.location.href);
    if (url.pathname == "/search" && url.searchParams.get('query') == value) return;

    global.websocket.add_onmessage((decrypted, _, self) => {
        if (decrypted.action != 'send-search-results') {global.websocket.pass_onmessage(self, decrypted, _); return;}
        
        update_search_results(decrypted.data);
        switch_page('search-results', false);
        global.websocket.remove_onmessage(self);
        document.title = `Search: ${value}`;
        window.history.pushState({id: "100"}, `Search: ${value}`, `/search?query=${btoa(value)}`);
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

function show_user_menu(add_callback = true) {
    document.getElementById('user-profile-box').getElementsByClassName('profile-scrolldown')[0].classList.add('shown');

    if (!add_callback) return;

    let old_callback = document.onclick;

    document.onclick = (event) => {
        if (old_callback) old_callback(event);

        if (document.getElementById('user-profile-box').contains(event.target)) return;

        hide_user_menu();

        document.onclick = old_callback;
    }
}

function switch_user_menu() {
    if (document.getElementById('user-profile-box').getElementsByClassName('profile-scrolldown')[0].classList.contains('shown')) {
        hide_user_menu();
    } else {
        show_user_menu();
    }
}

function update_search_suggestions(suggestions, assign_handler = true) {
    let suggestions_box = document.getElementById('search-bar').getElementsByClassName('search-suggestions')[0];
    if (suggestions.length == 0) { suggestions_box.classList.remove('shown'); return; }
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

    suggestions_box.classList.add('shown');

    if (!assign_handler) return;

    let old_callback = document.onclick;

    document.onclick = (event) => {
        if (old_callback) old_callback(event);

        if (document.getElementById('search-bar').contains(event.target)) return;

        update_search_suggestions([]);
        document.onclick = old_callback;
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
        service_logo: document.getElementById('content-page').getElementsByClassName('service-logo')[0],
        origin_url: document.getElementById('content-page').getElementsByClassName('origin-url')[0],
        image: document.getElementById('content-page').getElementsByClassName('image')[0],
        controls: document.getElementById('content-page').getElementsByClassName('controls')[0],

        description: document.getElementById('content-page').getElementsByClassName('description')[0],
        tags: document.getElementById('content-page').getElementsByClassName('tags')[0],

        trailer: document.getElementById('content-page').getElementsByClassName('trailer')[0],
        episodes: document.getElementById('content-page').getElementsByClassName('episodes')[0],
        sources: document.getElementById('content-page').getElementsByClassName('sources')[0],
        similar: document.getElementById('content-page').getElementsByClassName('similar')[0]
    }

    let url = new URL(window.location.href);
    if (url.pathname == "/content" && url.searchParams.get('uid') == content_uid) return;

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

    let content_data = await get_data;
    let service_data = await get_service_data(content_data.service);

    console.log(content_data, service_data);

    elements.title.innerText = content_data.title;
    elements.service_logo.src = location.origin + service_data.logo_url;
    elements.service_logo.dataset.url = service_data.homepage_url;
    elements.service_logo.setAttribute('onclick', 'open_url(this)');
    elements.origin_url.innerHTML = `<div class="label">Origin URL: </div><div class="url" onclick="open_url(this)" data-url="${content_data.url}">${content_data.url}</div>`;
    elements.image.src = content_data.thumbnail;
    elements.description.innerText = content_data.description.replaceAll('<newline>', '\n');

    elements.tags.innerHTML = '<div class="label">Tags:</div>';
    for (let tag of content_data.tags) {
        let tag_element = document.createElement('div');
        tag_element.classList.add('tag');
        tag_element.innerText = tag;
        elements.tags.appendChild(tag_element);
    }

    if (content_data.trailer) {
        let video = document.createElement('video');
        video.src = content_data.trailer;
        video.controls = true;
        elements.trailer.appendChild(video);
    }

    elements.episodes.innerHTML = '';
    for (let episode of content_data.episodes) {
        let episode_element = document.createElement('div');

        let details = document.createElement('div');

        let more_controls_menu = document.createElement('div');

        let play_button = document.createElement('div');
        let download_button = document.createElement('div');
        let more_button = document.createElement('div');
        
        let controls = document.createElement('div');

        let index = document.createElement('div');
        let title = document.createElement('div');
        let details_right = document.createElement('div');
        let origin_url = document.createElement('div');
        let language = document.createElement('div');

        more_controls_menu.classList.add('more-controls-menu');

        play_button.classList.add('play-button', 'button');
        download_button.classList.add('download-button', 'button');
        more_button.classList.add('more-button', 'button');
        
        index.classList.add('index');
        title.classList.add('title');
        origin_url.classList.add('origin-url');

        details_right.classList.add('details-right');

        controls.classList.add('controls');
        details.classList.add('details');
        language.classList.add('language');

        episode_element.classList.add('episode');

        play_button.setAttribute('data-icon', 'play');
        download_button.setAttribute('data-icon', 'download');
        more_button.setAttribute('data-icon', 'more');

        play_button = make_icon(play_button);
        download_button = make_icon(download_button);
        more_button = make_icon(more_button);

        play_button.setAttribute('onclick', `play('${episode.uid}')`);

        index.innerText = episode.index + ".";
        title.innerText = shorten_string(episode.title, 30);
        origin_url.innerText = episode.url;
        
        language.innerText = (episode.lang.toLowerCase() == "unknown" ? "unk" : episode.lang).toUpperCase();

        controls.appendChild(more_controls_menu);

        controls.appendChild(play_button);
        controls.appendChild(download_button);
        controls.appendChild(more_button);

        details_right.appendChild(title);
        details_right.appendChild(origin_url);

        details.appendChild(index);
        details.appendChild(details_right);

        episode_element.appendChild(controls);
        episode_element.appendChild(details);
        episode_element.appendChild(language);
        
        elements.episodes.appendChild(episode_element);
    }

    elements.similar.innerHTML = '';
    for (let similar of content_data.similar) {
        let similar_element = document.createElement('div');

        let thumbnail = document.createElement('img');
        let title = document.createElement('div');

        similar_element.classList.add('similar-element');
        thumbnail.classList.add('thumbnail');
        title.classList.add('title');

        thumbnail.src = similar.thumbnail;
        title.innerText = similar.title;

        similar_element.appendChild(thumbnail);
        similar_element.appendChild(title);

        elements.similar.appendChild(similar_element);
    }

    switch_page('content-page', false);
    changeFavicon(service_data.icon_url);
    document.title = content_data.title;
    window.history.pushState({id: "100"}, `Content: ${content_data.title}`, `/content?uid=${btoa(content_uid)}`);
}

async function get_service_data(service_name) {
    let promise = new Promise((resolve, reject) => {
        global.websocket.add_onmessage((decrypted, _, self) => {
            if (decrypted.action != 'send-service-info') {
                global.websocket.pass_onmessage(self, decrypted, _);
                return;
            }

            global.websocket.remove_onmessage(self);
            resolve(decrypted.data);
        })
    });

    global.websocket.send(JSON.stringify({
        action: 'get-service-info',
        data: {
            service_name: service_name
        }
    }));

    return await promise;
}

function open_url(url_or_element) {
    if (!url_or_element) return;

    let url = typeof url_or_element == 'string' ? url_or_element : url_or_element.dataset.url;
    let url_window = document.getElementById('url-popup');
    url_window.getElementsByClassName('url')[0].innerText = url;

    open_url_popup();
}

function open_url_popup() {
    document.getElementById('url-popup').classList.add('shown');
}

function close_url_popup() {
    document.getElementById('url-popup').classList.remove('shown');
}

function confirm_url_popup() {
    let url = document.getElementById('url-popup').getElementsByClassName('url')[0].innerText;
    window.open(url, '_blank');
    close_url_popup();
}

function content_switch_lower(switch_to) {
    let lower = document.getElementById('content-page').getElementsByClassName('lower')[0];

    let sections = Array.from(lower.getElementsByClassName('containers')[0].children).filter((element) => !element.classList.contains('controls'));

    for (let section of sections) {
        section.classList.remove('shown');
    }

    let new_section = document.getElementById('content-page').getElementsByClassName('lower')[0].getElementsByClassName(switch_to.toLowerCase())[0];
    new_section.classList.add('shown');

    document.getElementById('content-page').scrollTop = lower.getElementsByClassName('containers')[0].offsetTop - document.getElementById('pages-box').clientHeight + Math.min(new_section.clientHeight, 500);
}

async function play(episode_or_series_uid, optional_episode_index = -1) {
    let player_data = await new Promise((resolve, reject) => {
        global.websocket.add_onmessage((decrypted, _, self) => {
            if (decrypted.action != 'send-players-meta') {
                global.websocket.pass_onmessage(self, decrypted, _);
                return;
            }

            global.websocket.remove_onmessage(self);
            resolve(decrypted.data);
        });

        global.websocket.send(JSON.stringify({
            action: 'get-players-meta',
            data: {
                content_uid: episode_or_series_uid,
                user_id: global.user.info.id,
                token: global.user.info.token
            }
        }));
    }); 

    let top_quality = Math.max(...player_data.qualities.filter((quality) => quality != "unknown").map((quality) => parseInt(quality.slice(0, -1))));

    for (let source of player_data.sources) {
        if (source.quality == top_quality + "p") {
            global.websocket.send(JSON.stringify({
                action: 'get-player-data',
                data: {
                    media_uid: source.uid,
                    scrape: true,
                    user_id: global.user.info.id,
                    token: global.user.info.token
                }
            }));

            let full_player_data = await new Promise((resolve, reject) => {
                global.websocket.add_onmessage((decrypted, _, self) => {
                    if (decrypted.action != 'send-player-data') {
                        global.websocket.pass_onmessage(self, decrypted, _);
                        return;
                    }

                    global.websocket.remove_onmessage(self);
                    resolve(decrypted.data);
                });
                
            });

            console.log(full_player_data);

            open_video_player(full_player_data.url, false);
            break;
        }
    }
}

async function open_video_player(url, autoplay = false) {
    let video_player = document.getElementById('video-player');
    document.getElementById('video-player-window').classList.add('shown');
    
    video_player.src = url;
    if (autoplay) video_player.play();
}

function close_video_player() {
    document.getElementById('video-player').pause();
    document.getElementById('video-player-window').classList.remove('shown');
}
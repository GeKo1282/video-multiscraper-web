
addLoadEvent(() => {
    assign_player_handlers();
})

function assign_player_handlers() {
    document.addEventListener('fullscreenchange', fullScreenExitHandler, false);
    document.addEventListener('mozfullscreenchange', fullScreenExitHandler, false);
    document.addEventListener('MSFullscreenChange', fullScreenExitHandler, false);
    document.addEventListener('webkitfullscreenchange', fullScreenExitHandler, false);
    
    let video_player = document.getElementById('video-player');

    video_player.ontimeupdate = () => {
        let progressbar = document.querySelector("#video-player-window .controls .bottom .upper .progress-bar .progress-slider");
        progressbar.value = video_player.currentTime;
        player_progressbar_oninput(progressbar);
    }

    video_player.onplay = () => {
        if (!global.status_updater_running) {
            setTimeout(update_time_status, 2000, video_player.dataset.contentUid, true, true);
        }
    }
}

function update_time_status(content_uid, recurse = false, force = false) {
    if (document.getElementById('video-player').paused && !force) {
        global.status_updater_running = false;
        return;
    }

    global.status_updater_running = true;

    let video_player = document.getElementById('video-player');

    global.websocket.send(JSON.stringify({
        action: 'update-watch-progress',
        data: {
            content_uid: content_uid,
            user_id: global.user.info.id,
            token: global.user.info.token,
            progress: video_player.currentTime
        }
    }));

    if (!recurse) {
        global.status_updater_running = false;
        return;
    }

    setTimeout(update_time_status, 2000, content_uid, recurse, false);
}

function player_onkeydown(event) {
    if (event.key == " ") {
        playpause();
    } else if (event.key == "f") {
        toggle_player_fullscreen();
    } else if (event.key == "Escape") {
        exit_fullscreen();
    }
}

function fullScreenExitHandler() {
    if (document.webkitIsFullScreen || document.mozFullScreen || document.msFullscreenElement) return;

    exit_fullscreen();
}

function exit_fullscreen() {
    let fullscreen_control = document.querySelector("#video-player-window .controls .fullscreen-control");

    document.exitFullscreen();
    
    fullscreen_control.getElementsByClassName('icon-fullscreen')[0].classList.remove('hidden');
    fullscreen_control.getElementsByClassName('icon-fullscreen-exit')[0].classList.add('hidden');
}

function enter_player_fullscreen() {
    let fullscreen_control = document.querySelector("#video-player-window .controls .fullscreen-control");

    document.querySelector("#video-player-window .video-player").requestFullscreen();

    fullscreen_control.getElementsByClassName('icon-fullscreen')[0].classList.add('hidden');
    fullscreen_control.getElementsByClassName('icon-fullscreen-exit')[0].classList.remove('hidden');
}

function toggle_player_fullscreen() {
    if (document.webkitIsFullScreen || document.mozFullScreen || document.msFullscreenElement) {
        exit_fullscreen();
    } else {
        enter_player_fullscreen();
    }
}

async function play(content_uid, title, optional_episode_index = -1) {
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
                content_uid: content_uid,
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

                    console.log(decrypted)

                    global.websocket.remove_onmessage(self);
                    resolve(decrypted.data);
                });
                
            });

            console.log(full_player_data);

            open_video_player(full_player_data.url, content_uid, title, false);
            break;
        }
    }
}

async function open_video_player(url, content_uid, title = null, autoplay = true) {
    let video_player = document.getElementById('video-player');
    let progressbar = document.querySelector("#video-player-window .controls .bottom .upper .progress-bar .progress-slider");
    let total_time = document.querySelector("#video-player-window .controls .bottom .total-time");
    let title_box = document.querySelector("#video-player-window .controls .top .title");
    document.getElementById('video-player-window').classList.add('shown');

    if (title) title_box.innerText = title; else title_box.innerText = "";
    
    video_player.onloadedmetadata = () => {
        progressbar.step = 1;
        progressbar.value = 0;
        progressbar.max = video_player.duration;
        total_time.innerText = format_time(parseInt(video_player.duration));
    }

    video_player.src = url;
    video_player.dataset.contentUid = content_uid;
    if (autoplay) video_player.play();
}

function close_video_player() {
    document.getElementById('video-player').pause();
    document.getElementById('video-player-window').classList.remove('shown');
}

function playpause() {
    let video = document.getElementById('video-player');
    if (video.paused) {
        video.play();
    } else {
        video.pause();
    }
}

function player_progressbar_onmousedown(element) {
    let video_player = document.getElementById('video-player');

    if (!video_player.paused) {
        video_player.pause();
        element.dataset.unpause = true;
    }
}

function player_progressbar_onchange(element) {
    let video_player = document.getElementById('video-player');

    video_player.currentTime = element.value;

    if (element.dataset.unpause) {
        video_player.play();
        delete element.dataset.unpause;
    }
}

function player_progressbar_oninput(element) {
    let progressbar = document.querySelector("#video-player-window .controls .bottom .upper .progress-bar");
    let current_time = document.querySelector("#video-player-window .controls .bottom .current-time");

    progressbar.setAttribute("style", `--progress: ${element.value / element.max * 100}%`);
    current_time.innerText = format_time(parseInt(element.value));
}

function player_volume_oninput(element) {
    let video_player = document.getElementById('video-player');

    if (global.user.settings.volume.type == "exponential") {
        video_player.volume = element.value ** global.user.settings.volume.volume_exponent / (10 ** global.user.settings.volume.volume_exponent) / 100;
    } else if (global.user.settings.volume.type == "linear") {
        video_player.volume = element.value / 100;
    }
}
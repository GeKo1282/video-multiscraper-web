addLoadEvent(async () => {
    await new Promise((resolve, reject) => {
        if (global.websocket && global.websocket.ready) resolve();

        if (!global.websocket_triggers) global.websocket_triggers = [];

        global.websocket_triggers.push(resolve);
    })

    update_watched_section();
    add_page_switch_callback("user-home-page", async () => {
        update_watched_section();
    });
});

async function update_watched_section() {
    async function tile_factory(tile_data) {
        let block = document.createElement("div");

        let img = document.createElement("img");

        let details = document.createElement("div");

        let top = document.createElement("div");

        let title = document.createElement("div");
        let progress = document.createElement("div");

        let progress_bar = document.createElement("div");

        let option_menu = document.createElement("div");

        block.classList.add("watched-tile");
        block.setAttribute("onclick", `play("${tile_data.uid}")`);

        img.classList.add("thumbnail");
        img.src = "/cdn/media/" + tile_data.series.uid + "/thumbnail";

        if (!tile_data.series.title) {
            tile_data.series = await new Promise((resolve, reject) => {
                global.websocket.add_onmessage((decrypted, _, self) => {
                    if (decrypted.action != 'send-content-info') {
                        global.websocket.pass_onmessage(self, decrypted, _);
                        return;
                    }
        
                    global.websocket.remove_onmessage(self);
                    resolve(decrypted.data);
                })

                global.websocket.send(JSON.stringify({
                    action: "get-content-info",
                    data: {
                        user_id: global.user.info.id,
                        token: global.user.info.token,
                        content_uid: tile_data.series.uid
                    }
                }));
            });
        }


        title.innerText = tile_data.series.title;
        title.classList.add("title");

        progress.classList.add("progress");
        progress.innerText = "";
        if(tile_data.season && tile_data.season.index) {
            progress.innerText += `S${tile_data.season.index}:`
        }

        progress.innerText += `E${tile_data.index}`;

        progress_bar.classList.add("progress-bar");
        progress_bar.style.transform = `scaleX(${tile_data.progress / tile_data.total})`;

        option_menu.classList.add("option-menu");

        details.classList.add("details");
        top.classList.add("top");

        top.appendChild(title);
        top.appendChild(progress);
        
        details.appendChild(top);
        details.appendChild(progress_bar);
        details.appendChild(option_menu);

        block.appendChild(img);
        block.appendChild(details);

        return block;
    }

    function deduplicate(watched_states) {
        const date_based = true;
        const min_time_diff = 15 * 60;
        let deduped = [];

        for (let watched_state of watched_states) {
            let found = deduped.find(x => x.series.uid == watched_state.series.uid);

            if ((found && found.index > watched_state.index && (!date_based || Math.abs(found.updated - watched_state.updated) < min_time_diff)) || (found && found.updated > watched_state.updated && date_based && Math.abs(found.updated - watched_state.updated) > min_time_diff)) {
                continue;
            } else {
                deduped.splice(deduped.indexOf(found), 1);
            }

            deduped.push(watched_state);
        }

        return deduped;
    }

    document.querySelector("#user-home-page .recently-watched .vertical-scroll").innerHTML = "";

    let watched_states = deduplicate(await get_watch_progress("all", true));
    
    for (let watched_state of watched_states) {
        let tile = await tile_factory(watched_state);
        document.querySelector("#user-home-page .recently-watched .vertical-scroll").appendChild(tile);
    }
}
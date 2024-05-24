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
    function tile_factory(tile_data) {
        
    }

    let watched_states = await get_watch_progress("all", true);
    console.log(watched_states);
}
addLoadEvent(async () => {
    // Temporay test
    await sleep(2000);

    document.getElementById('homepage-window').classList.remove('shown');
    document.getElementById('someother-window').classList.add('shown');
})

addLoadEvent(() => {
    assign_clicks();
})

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
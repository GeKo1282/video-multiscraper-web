addLoadEvent(async () => {
    await sleep(2000);

    document.getElementById('homepage-window').classList.remove('shown');
    document.getElementById('someother-window').classList.add('shown');
})
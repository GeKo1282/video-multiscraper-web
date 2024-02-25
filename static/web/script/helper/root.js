if (!window.global) window.global = {};
global = window.global;

addLoadEvent(() => {
    assign_validators();
})

function assign_validators() {
    for (let input of document.getElementsByClassName('validate')) {
        if (input.dataset.validatorStandard) {
            make_validator(input, make_validator_function('standard', input.dataset.validatorStandard));
        } else if (input.dataset.regexValidator) {
            make_validator(input, make_validator_function('regex', input.dataset.regexValidator));
        } else if (input.dataset.customValidator) {
            make_validator(input, make_validator_function('custom', input.dataset.customValidator));
        }
    }
}

function switch_window(id, close_all_windows = true) {
    if (close_all_windows) close_layer_windows(Array.from(document.body.getElementsByClassName('layer')).map(layer => layer.id));

    if (!close_all_windows) {
        let object = document.getElementById(id);
        while (!object.parentElement.classList.contains('layer') || object.parentElement.parentElement != document.body || object == document.body) {
            object = object.parentElement;
        }

        if (object == document.body) return;

        close_layer_windows(object.parentElement.id);
    }

    open_window(id);
}

function close_layer_windows(layers) {
    if (!Array.isArray(layers)) layers = [layers];
    for (let layer of layers) {
        if (!layer.endsWith('-layer')) layer = layer + '-layer';
        for (let window of document.getElementById(layer).getElementsByClassName('window')) {
           window.classList.remove('shown');            
        }
    }
}

function open_window(id) {
    document.getElementById(id).classList.add('shown');
}
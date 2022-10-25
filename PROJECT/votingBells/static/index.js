document.addEventListener('DOMContentLoaded', () => {

// Подключиться к веб-сокету
    var socket = io.connect(location.protocol + '//' + document.domain + ':' + location.port);

    // При подключении настройте кнопки
    socket.on('connect', () => {
        // Каждая кнопка должна создать событие "submit vote"
        document.querySelectorAll('button').forEach(button => {
            button.onclick = () => {
                const selection = button.dataset.vote;
                socket.emit('submit vote', {'selection': selection});
            };
        });
    });

//     Когда будет объявлено новое голосование, добавьте в неупорядоченный список
//    socket.on('announce vote', data => {
//        alert(data.selection)
//        const li = document.createElement('li');
//        li.innerHTML = `Vote recorded: ${data.selection}`;
//        document.querySelector('#votes').append(li);
//    });

    socket.on('vote totals', data => {
        document.querySelector('#yes').innerHTML = data.yes;
        document.querySelector('#no').innerHTML = data.no;
        document.querySelector('#maybe').innerHTML = data.maybe;
    });
});
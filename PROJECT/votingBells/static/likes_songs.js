document.addEventListener('DOMContentLoaded', () => {

    var socket = io.connect(location.protocol + '//' + document.domain + ':' + location.port);
    socket.on('connect', () => {
        document.querySelectorAll('button').forEach(button => {
            button.onclick = () => {
                const id = button.dataset.id;
                const choice = button.dataset.choice;

                socket.emit('likes songs', [id, choice]);
            };
        });
    });

    socket.on('vote totals songs', data => {
        document.querySelector('#likes_' + data[1]).innerHTML = data[0];
        document.querySelector('#bells').innerHTML = 'Bells - ' + data[2];
    });
});
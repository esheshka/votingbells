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

    });

    socket.on('show bells', data => {
        socket.emit('get bells');
    });

    socket.on('show bells self', count => {
        document.querySelector('#bells').innerHTML = 'Bells - ' + count;
    });

    socket.on('is approve song', data => {
        if (data[1] == 0) {
            document.querySelectorAll('.total_' + data[0]).forEach(e => e.parentNode.removeChild(e));
        }
    });
});
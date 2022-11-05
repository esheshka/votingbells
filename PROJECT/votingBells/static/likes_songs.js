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

    socket.on('show my likes song', data => {
        const user_likes = document.querySelectorAll('.user_likes_' + data[0]);
        for (var i=0; i < user_likes.length; i++) {
            user_likes[i].innerHTML = data[1];
        }
    });

    socket.on('vote totals songs', data => {
        likes = document.querySelectorAll('.likes_' + data[1]);
        for (var i=0; i<likes.length; i++) {
            likes[i].innerHTML = data[0] + ' | ';
        }
    });

    socket.on('show bells', data => {
        socket.emit('get bells');
    });

    socket.on('show bells self', count => {
        document.querySelector('#bells').innerHTML = 'Bells - ' + count;
    });

    socket.on('is approve group', data => {
        if (data[1] == 0) {
            total = document.querySelectorAll('.total_' + data[0]);
            for (var i=0; i<total.length; i++) {
                total[i].forEach(e => e.parentNode.removeChild(e));
            }
        }
    });
});
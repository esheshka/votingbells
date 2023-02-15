document.addEventListener('DOMContentLoaded', () => {

    var socket = io.connect(location.protocol + '//' + document.domain + ':' + location.port);
    socket.on('connect', () => {
        document.querySelectorAll('button').forEach(button => {
            button.onclick = () => {
                const id = button.dataset.id;
                const approve = button.dataset.approve;
                const song_name = document.querySelector('#input_name_song' + id).value;
                const band_name = document.querySelector('#input_name_band' + id).value;

                socket.emit('approve song', [id, approve, song_name, band_name]);
            };
        });
    });

    socket.on('is approve song', data => {
        document.querySelectorAll('.total_' + data[0]).forEach(e => e.parentNode.removeChild(e));
    });
});
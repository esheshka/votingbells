document.addEventListener('DOMContentLoaded', () => {

    var socket = io.connect(location.protocol + '//' + document.domain + ':' + location.port);
    socket.on('connect', () => {
        document.querySelectorAll('button').forEach(button => {
            button.onclick = () => {
                const id = button.dataset.id;
                const approve = button.dataset.approve;
                const group_name = document.querySelector('#input_name_group' + id).value;

                socket.emit('approve group', [id, approve, group_name]);
            };
        });
    });

    socket.on('is approve group', data => {
        document.querySelectorAll('.total_' + data[0]).forEach(e => e.parentNode.removeChild(e));
    });
});
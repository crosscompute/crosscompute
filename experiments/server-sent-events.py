from pyramid.config import Configurator
from pyramid.response import Response
from time import sleep
from waitress import serve


def see_home(request):
    return Response('''\
<html>
<head>
</head>
<body>
<div id="ping"></div>
<div id="x"></div>
<script>
    const eventSource = new EventSource('/echoes')
    eventSource.onmessage = function(event) {
        console.log(event)

        const { data } = event
        console.log(data)

        switch(data) {
            case '':
                // ping
                e = document.getElementById('ping')
                e.innerHTML += 'ping '
                break
            case '*':
                // refresh
                location.reload()
                break
            default:
                // update
                d = JSON.parse(data)
                e = document.getElementById(d['#'])
                e.innerHTML = JSON.stringify(d['?'])
        }
    }
</script>
</body>
</html>''')


def send_echoes(request):
    response = Response(headerlist=[
        ('Content-Type', 'text/event-stream'),
        ('Cache-Control', 'no-cache'),
    ])
    response.app_iter = yield_echoes()
    return response


def yield_echoes():
    print('ping')
    yield 'data:\n\n'.encode()
    sleep(3)
    print('update')
    yield 'data: {"#": "x", "?": {"a": 1}}\n\n'.encode()
    sleep(3)
    print('refresh')
    yield 'data: *\n\n'.encode()


with Configurator() as config:
    config.add_route('home', '/')
    config.add_route('echoes', '/echoes')
    config.add_view(see_home, route_name='home')
    config.add_view(send_echoes, route_name='echoes')
    app = config.make_wsgi_app()
serve(app, port=8000)

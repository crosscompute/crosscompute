from argparse import ArgumentParser
from pyramid.config import Configurator
from waitress import serve

from crosscompute.routines import (
    configure_argument_parser_for_logging,
    configure_logging_from)


AUTOMATION_ROUTE = '/a/{automation_slug}'
BATCH_ROUTE = '/b/{batch_slug}'
VARIABLE_ROUTE = '/{variable_type}/{variable_path}'


if __name__ == '__main__':
    a = ArgumentParser()
    a.add_argument('--host', default='127.0.0.1')
    a.add_argument('--port', default='7000')
    configure_argument_parser_for_logging(a)
    args = a.parse_args()

    configure_logging_from(args)

    with Configurator() as config:
        config.include('pyramid_jinja2')

        config.add_route('home', '/')
        config.add_route('automation', AUTOMATION_ROUTE)
        config.add_route('automation batch', AUTOMATION_ROUTE + BATCH_ROUTE)
        config.add_route(
            'automation batch variable',
            AUTOMATION_ROUTE + BATCH_ROUTE + VARIABLE_ROUTE)
        
        config.add_view(
            home,
            route_name='home',
            renderer='home.jinja2')
    app = config.make_wsgi_app()

    serve(app, host=args.host, port=args.port)

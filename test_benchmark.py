# -*- coding: utf-8 -*-

import re
import random
import configparser
from itertools import combinations
from functools import partial
from shunting.shuntbox import Router as ShuntingRouter, HTTP_METHODS
from sanic.router import Router as SanicRouter
from collections import namedtuple
from sanic.exceptions import NotFound, InvalidUsage
from japronto.router import Router as ProntoRouter
from autoroutes import Routes


METHODS = list(combinations(HTTP_METHODS, 2))
Request = namedtuple('Request', ['path', 'method'])


def dummy():
    return 'dummy'


def scrambled(orig):
    dest = orig[:]
    random.shuffle(dest)
    return dest


if __name__ == "__main__":
    
    config = configparser.ConfigParser()
    config.sections()
    config.read('urls.ini')
    routes = []

    # Read the routes
    for pattern, controller in config['urls'].items():
        methods = random.choice(METHODS)
        method_dict = dict([(method, controller) for method in methods])
        routes.append((pattern, controller, methods, method_dict))

    random.shuffle(routes)  # We randomize the routes

    # Read the requests
    requests = [
        (url.strip(), random.choice(list(HTTP_METHODS)))
        for url, _ in config['queries'].items()]
    random.shuffle(requests)  # we randomize the requests


    def shunting_add_routes(routes):
        router = ShuntingRouter()
        for url, controller, methods, method_dict in routes:
            router.add(url, **method_dict)
        return router

    def autoroutes_add_routes(routes):
        router = Routes()
        for url, controller, methods, method_dict in routes:
            router.add(url, methods=method_dict)
        return router
    
    def sanic_add_routes(routes):
        router = SanicRouter()
        for url, controller, methods, method_dict in routes:
            router.add(url, methods, controller)
        return router

    def japronto_add_routes(routes):
        router = ProntoRouter()
        for url, controller, methods, method_dict in routes:
            try:
                if len(methods) > 1:
                    router.add_route(url, dummy, methods=methods)
                else:
                    router.add_route(url, dummy, method=methods[0])
            except ValueError:
                # Japronto don't accept several unnamed {} patterns
                pass
        return router.get_matcher()

    def test_shunting(router):
        for url, method in requests:
            yield router.lookup(url, method)

    def test_autoroutes(router):
        for url, method in requests:
            # autoroutes don't match method
            yield url, method, router.match(url)

    def test_japronto(router):
        for url, method in requests:
            yield url, method, router.match_request(Request(url, method))

    def test_sanic(router):
        for url, method in requests:
            try:
                yield url, method, router.get(Request(url, method))
            except (NotFound, InvalidUsage):
                pass


    # Add routes to the module level routers.
    router = shunting_add_routes(routes)
    arouter = autoroutes_add_routes(routes)
    srouter = sanic_add_routes(routes)
    jrouter = japronto_add_routes(routes)

    #import pprint
    #pp = pprint.PrettyPrinter(indent=4)
    
    #pp.pprint(list(test_shunting(router)))
    #exit()
    
    import timeit
    iterations = 10000
    globs = globals()

    print(
        'Shunting route registration: ',
        timeit.timeit(
            'shunting_add_routes(routes)', number=iterations, globals=globs),
        'sec.',
    )
    print(
        'Shunting route lookup: ',
        timeit.timeit(
            'list(test_shunting(router))', number=iterations, globals=globs),
        'sec.',
    )

    print('=' * 40)
    
    print(
        'Sanic route registration: ',
        timeit.timeit(
            'sanic_add_routes(routes)', number=iterations, globals=globs),
        'sec.'
    )
    print(
        'Sanic route lookup: ',
        timeit.timeit(
            'list(test_sanic(srouter))', number=iterations, globals=globs),
        'sec.'
    )
    
    print('=' * 40)
    
    print(
        'Japronto routes registration: ',
        timeit.timeit(
            'japronto_add_routes(routes)', number=iterations, globals=globs),
        'sec.',
    )
    print(
        'Japronto route lookup: ',
        timeit.timeit(
            'list(test_japronto(jrouter))', number=iterations, globals=globs),
        'sec.',
    )

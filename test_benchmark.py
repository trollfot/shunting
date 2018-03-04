# -*- coding: utf-8 -*-

import re
import random
import configparser
from itertools import combinations
from functools import partial
from shunting.router import Router as ShuntingRouter, HTTP_METHODS
from sanic.router import Router as SanicRouter
from collections import namedtuple
from sanic.exceptions import NotFound, InvalidUsage
from japronto.router import Router as ProntoRouter


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
    
    for pattern, controller in config['urls'].items():
        methods = random.choice(METHODS)
        method_dict = dict([(method, controller) for method in methods])
        routes.append((pattern, controller, methods, method_dict))

    random.shuffle(routes)  # We randomize the routes

    
    requests = [
        (url.strip(), random.choice(list(HTTP_METHODS)))
        for url, _ in config['queries'].items()]
    random.shuffle(requests)  # we randomize the requests


    def shunting_add_routes(routes):
        router = ShuntingRouter()
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
        return router
                

    def test_shunting(router):
        for url, method in requests:
            router.select(url, method)

    
    def test_japronto(router):
        for url, method in requests:
            router.match_request(Request(url, method))


    def test_sanic(router):
        for url, method in requests:
            try:
                router.get(Request(url, method))
            except (NotFound, InvalidUsage):
                pass


    import timeit
    iterations = 1000
    globs = globals()

    print(timeit.timeit(
        'shunting_add_routes(routes)', number=iterations, globals=globs))
    print(timeit.timeit(
        'sanic_add_routes(routes)', number=iterations, globals=globs))
    print(timeit.timeit(
        'japronto_add_routes(routes)', number=iterations, globals=globs))

    router = shunting_add_routes(routes)
    srouter = sanic_add_routes(routes)
    jrouter = japronto_add_routes(routes).get_matcher()

    globs = globals()
    print(timeit.timeit(
        'test_shunting(router)', number=iterations, globals=globs))
    print(timeit.timeit(
        'test_sanic(srouter)', number=iterations, globals=globs))
    print(timeit.timeit(
        'test_japronto(jrouter)', number=iterations, globals=globs))

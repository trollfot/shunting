# -*- coding: utf-8 -*-

import autoroutes
from collections import namedtuple, defaultdict
from functools import lru_cache



ROUTER_CACHE_SIZE = 1024
HTTP_METHODS = frozenset((
    'GET', 'POST', 'PUT', 'HEAD', 'OPTIONS', 'PATCH', 'DELETE', 'ANY'))

Found = namedtuple('Found', ['method', 'handler', 'params', 'consumed'])
NotSupported = object()
NotFound = object()


class RouteHandlerUndefined(autoroutes.InvalidRoute):
    pass


class RouteMethodAlreadyImplemented(autoroutes.InvalidRoute):
    pass


class Router:

    def __init__(self, prefix=""):
        self.prefix = prefix
        self.routes = autoroutes.Routes()
        self._seen = defaultdict(set)

    def add(self, path, prefix="", **methods):
        if not methods:
            raise RouteHandlerUndefined(
                "No handlers specified for {}".format(path))
        adding = frozenset(methods.keys())
        unknown = adding - HTTP_METHODS
        if unknown:
            raise KeyError(
                'Route defines an unknown HTTP method(s): {}.'.format(unknown))

        pattern = (prefix or self.prefix) + path
        seen = self._seen[pattern]

        if not seen:
            seen.update(adding)
        else:
            existing = seen & adding
            if existing:
                raise RouteMethodAlreadyImplemented(
                    'Route {} already has a handler for {}.'.format(
                        path, existing))
            seen.update(adding)
        self.routes.add(pattern, **methods)


    def lookup(self, path, method):
        payload, params = self.routes.match(path)
        if payload:
            if method in payload:
                return Found(method, payload[method], params, path)
            if 'ANY' in payload:
                return Found(method, payload['ANY'], params, path)
            return NotSupported
        return NotFound


if __name__ == '__main__':
    router = Router()
    router.add('/path/to/view', POST='post_handler')
    router.add('/path/to/view', ANY='other_handler')
    router.add('/path/to/view', POST='faulty_handler')
    print(router.lookup('/path/to/view', 'POST'))

# -*- coding: utf-8 -*-

import regex
from collections import namedtuple, defaultdict
from functools import lru_cache


HTTP_METHODS = frozenset((
    'GET', 'POST', 'PUT', 'HEAD', 'OPTIONS', 'PATCH', 'DELETE'))


ANY = '_ANY_'
ROUTER_CACHE_SIZE = 1024


Route = namedtuple(
    'Route', ['path', 'pattern', 'methods', 'handlers', 'complexity'])
Found = namedtuple(
    'Found', ['route', 'params', 'consumed'])

NotSupported = object()
NotFound = object()


def discriminate(url):
    return url.count('/')


def parse_route_options(s):
    def walker(level=0):
        try:
            token = ''
            while tokens:
                char = next(tokens)
                if char == ']':
                    if level == 0:
                        raise Exception('missing opening paren')
                    else:
                        return [token]
                elif char == '[':
                    return [token] + [walker(level+1)] + walker(level)
                else:
                    token += char
        except StopIteration:
            if level != 0:
                raise Exception('missing closing paren')
            else:
                return [token]

    tokens = iter(s)
    return walker()


def unfold_routes(pattern):
    
    def all_possiblities(args):
        if args and len(args) > 0:
            values, *rest = args
            for possibility in all_possiblities(rest):
                yield [None] + possibility
                for value in values:
                    yield [value] + possibility
        else:
            yield []
 
    def generate(items):
        choices = []
        indexes = []
        model = []

        for index, item in enumerate(items):
            if isinstance(item, list):
                indexes.append(index)
                choices.append(list(generate(item)))
                model.append(None)
            else:
                model.append(item)

        for possiblity in all_possiblities(tuple(choices)):
            line = list(model)
            for index, value in enumerate(possiblity):
                line[indexes[index]] = value
            yield ''.join(value for value in line if value)

    options = parse_route_options(pattern)
    return generate(options)


class SimpleParser:
    start, end = '{}'
    vfinder = regex.compile('\{(\w*)(:(\w+))?\}')
    ofinder = regex.compile('\[.*\]')

    _patterns = {
        'word': r'\w+',
        'alpha': r'[a-zA-Z]+',
        'digits': r'\d+',
        'number': r'\d*.?\d+',
        'chunk': r'[^/^.]+',
        'segment': r'[^/]+',
        'any': r'.+',
    }

    default_pattern = 'chunk'

    def __init__(self, patterns=None):
        self.patterns = dict(self._patterns)
        if patterns is not None:
            self.patterns.update(patterns)

    def create_pattern(self, url):
        nbvars = 0
        start = 0
        route_pattern = ''
        names = set()
        for idx, param in enumerate(self.vfinder.finditer(url), 1):
            span, values = param.span(), param.groups()
            name, _, pname = values
            if not name:
                name = "_param_{}".format(idx)

            if not name in names:
                names.add(name)
            else:
                raise KeyError(
                    'Variable name {} already exists ({})'.format(name, url))
                
            if not pname:
                pname = self.default_pattern
            pattern = self.patterns[pname]  # we need to test.

            if start <= span[0]:
                # We maybe just be consecutive
                route_pattern += regex.escape(url[start:span[0]])

            nbvars += 1
            route_pattern += '(?P<%s>%s)' % (name, pattern)
            start = span[1]
        if start and start < len(url):
            route_pattern += regex.escape(url[start:])
        if not route_pattern:
            return nbvars, url
        return nbvars,  "^{}$".format(route_pattern)

    def __call__(self, url_pattern):
        if not self.ofinder.search(url_pattern):
            yield self.create_pattern(url_pattern)
        else:
            yield from map(self.create_pattern, unfold_routes(url_pattern))


class Router:

    def __init__(self, parser=None, prefix=""):
        if parser is None:
            parser = SimpleParser()
        self.parser = parser
        self.prefix = prefix
        self.regexp_routes = defaultdict(dict)
        self._complex_routes = {}
        self.direct_routes = {}

    def add(self, path, methods, prefix=None):
        if prefix is None:
            prefix = self.prefix

        adding = frozenset(methods.keys())
        if not adding <= HTTP_METHODS:
            raise KeyError('Route defines an unknown HTTP method.')

        def merge_route(route, methods):
            overlapping = adding & route.methods
            if overlapping:
                raise KeyError(
                    'Route {} already has method(s): {}'.format(
                        route.path, overlapping))
            handlers = route.handlers
            handlers.update(methods)
            return Route(
                route.path, route.pattern,
                frozenset(methods.keys()), handlers, route.complexity)

        for nbvars, pattern in self.parser(prefix + path):
            if nbvars:
                discriminant = discriminate(pattern)
                routes = self.regexp_routes[discriminant]
                route = routes.get(pattern, None)
                if route is not None:
                    new_route = merge_route(route, methods)
                    routes[pattern] = new_route
                else:
                    compiled = regex.compile(pattern)
                    routes[pattern] = Route(
                        pattern, compiled, adding, methods, nbvars)
                self._complex_routes[discriminant] = tuple(routes.values())
            else:
                route = self.direct_routes.get(pattern, None)
                if route is not None:
                    new_route = merge_route(route, methods)
                    self.direct_routes[pattern] = new_route
                else:
                    self.direct_routes[pattern] = Route(
                        pattern, None, adding, methods, nbvars)

    #@lru_cache(maxsize=ROUTER_CACHE_SIZE)
    def select(self, path, method):
        """Figure out which app to delegate to or send 404 or 405.
        """
        found = False
        route = self.direct_routes.get(path, None)
        if route is not None:
            if method in route.methods or ANY in route.methods:
                return Found(route, {}, path)
            else:
                found = True

        discriminant = discriminate(path)
        if discriminant in self._complex_routes:
            for route in self._complex_routes[discriminant]:
                match = route.pattern.match(route.path)
                if match:
                    if not method in route.methods:
                        if not ANY in route.methods:
                            found = True
                            continue
                    return Found(route, match.groupdict(), match.group(0))
        return found and NotSupported or NotFound

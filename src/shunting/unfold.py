# -*- coding: utf-8 -*-

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

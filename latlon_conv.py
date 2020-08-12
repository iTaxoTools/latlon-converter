#!/usr/bin/env python3
import re
from typing import List, Tuple, Union

Tokens = List[Tuple[int, str]]
Minute = Union[float, Tuple[int, float]]
Coordinate = Union[float, Tuple[int, Minute]]


def prepare_string(string: str) -> str:
    """
    standardizes the string
    """
    string = string.casefold()
    string = re.sub('north', 'n', string)
    string = re.sub('south', 's', string)
    string = re.sub('west', 'w', string)
    string = re.sub('east', 'e', string)
    string = re.sub(
        'seconds|sec|["“”‟]|[´`‘’‛][´`‘’‛]|[´`‘’‛] [´`‘’‛]', "''", string)
    string = re.sub('minutes|min|[´`‘’‛]', "'", string)
    string = re.sub('degrees|deg|o', '°', string)
    return string


def parse_coord(tokens: Tokens) -> Tuple[Coordinate, Tokens]:
    """
    parse a single coordinate and return the rest of the string

    raises a ValueError("parse error") if the beginning doesn't match a coordinate
    """
    # deal with the simple situations
    if not tokens:
        raise ValueError("parse error")
    elif len(tokens) == 1:
        return tokens[0][0], tokens[1:]

    first_sep = tokens[0][1]
    if first_sep[0] in '.,':
        # parse floating point coordinate
        return parse_float(tokens)
    elif first_sep[0] == '°':
        # parse degree, minutes coordinate
        degrees = tokens[0][0]
        try:
            minutes, tokens1 = parse_minutes(tokens[1:])
            return (degrees, minutes), tokens1
        except ValueError:
            # there is no minutes
            return (float(degrees), tokens[1:])
    else:
        raise ValueError("parse error")


def parse_float(tokens: Tokens) -> Tuple[float, Tokens]:
    """
    parse a float and return the rest of the string

    raise a ValueError("parse error") if the length is less than two
    """
    if len(tokens) < 2:
        raise ValueError("parse error")
    else:
        int_part = tokens[0][0]
        dec_part = tokens[1][0]
        return (float(str(int_part) + '.' + str(dec_part)), tokens[2:])


def parse_minutes(tokens: Tokens) -> Tuple[Minute, Tokens]:
    """
    parse a coordinate starting with minutes and return the rest of the string

    raises a ValueError("parse error"), if the parsing fails
    """
    # deal with the simple situations
    if not tokens:
        raise ValueError("parse error")
    elif len(tokens) == 1:
        return tokens[0][0], tokens[1:]

    first_sep = tokens[0][1]
    if first_sep[0] in '.,':
        # parse floating point minutes
        return parse_float(tokens)
    elif first_sep[0] == "'":
        # parse minutes, seconds
        minutes = tokens[0][0]
        try:
            seconds, tokens1 = parse_seconds(tokens[1:])
            return ((minutes, seconds), tokens1)
        except ValueError:
            # there is no seconds
            return (float(minutes), tokens[1:])
    else:
        raise ValueError("parse error")


def parse_seconds(tokens: Tokens) -> Tuple[float, Tokens]:
    """
    parse a coordinate starting with seconds and return the rest of the string

    raises a ValueError("parse error"), if the parsing fails
    """
    # deal with the simple situations
    if not tokens:
        raise ValueError("parse error")
    elif len(tokens) == 1:
        return tokens[0][0], tokens[1:]

    first_sep = tokens[0][1]
    if first_sep[0] in '.,':
        # parse floating point seconds
        return parse_float(tokens)
    elif first_sep[0:2] == "''":
        # parse seconds
        return tokens[0][0], tokens[1:]
    else:
        raise ValueError("parse error")


def hemisphere_sign(c: str, coord: Coordinate) -> Coordinate:
    if c in 'NE':
        return coord
    else:
        if isinstance(coord, float):
            return -coord
        else:
            if isinstance(coord[1], float):
                return (-coord[0], -coord[1])
            else:
                return (-coord[0], (-coord[1][0], -coord[1][1]))


def parse_coordinates(string: str) -> Tuple[Coordinate, Coordinate]:
    """
    parses a string into coordinates with longitude first

    if the whole string is not consumed, raises a ValueError with the rest
    """
    string = prepare_string(string)
    quadrant = [c for c in string if c in 'NSEW']
    if not quadrant:
        def orient(p: Tuple[Coordinate, Coordinate]
                   ) -> Tuple[Coordinate, Coordinate]: return p
    elif len(quadrant) == 2:
        if quadrant[0] in 'NS' and quadrant[1] in 'WE':
            def swap(p: Tuple[Coordinate, Coordinate]) -> Tuple[Coordinate, Coordinate]:
                return p
        elif quadrant[0] in 'WE' and quadrant[1] in 'NS':
            def swap(p: Tuple[Coordinate, Coordinate]) -> Tuple[Coordinate, Coordinate]:
                return (p[1], p[0])

        def orient(p: Tuple[Coordinate, Coordinate]) -> Tuple[Coordinate, Coordinate]:
            return swap((hemisphere_sign(quadrant[0], p[0]), hemisphere_sign(quadrant[1], p[1])))
    tokens = [(int(m.group(1)), m.group(2))
              for m in re.finditer(r'(-?\d+)([^\d-]*)', string)]
    coord0, tokens1 = parse_coord(tokens)
    coord1, rest = parse_coord(tokens1)
    if rest:
        raise ValueError(''.join(str(n)+sep for n, sep in rest))
    else:
        return orient((coord0, coord1))

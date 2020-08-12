#!/usr/bin/env python3
import re
import math
import sys
from typing import List, Tuple, Union, Iterator

# the parsers' input type
Tokens = List[Tuple[int, str]]
# types of minutes: either a float or int with seconds
Minute = Union[float, Tuple[int, float]]
# type of coordinates: either a float or sign, degree and minutes
Coordinate = Union[float, Tuple[bool, int, Minute]]


def dec_minute(minute: Minute) -> float:
    if isinstance(minute, float):
        return minute
    else:
        return minute[0] + minute[1] / 60


def dec_coord(coord: Coordinate) -> float:
    if isinstance(coord, float):
        return coord
    else:
        return (1 if coord[0] else -1) * (coord[1] + dec_minute(coord[2]) / 60)


def sx_coord(coord: Coordinate) -> Tuple[bool, int, Tuple[int, float]]:
    if isinstance(coord, float):
        sign = coord >= 0
        coord = abs(coord)
        deg = math.floor(coord)
        return sx_coord((sign, deg, (coord - deg) * 60))
    else:
        sign, deg, mm = coord
        if isinstance(mm, float):
            mm_int = math.floor(mm)
            sec = (mm - mm_int) * 60
            return (sign, deg, (mm_int, sec))
        else:
            return (sign, deg, mm)


def str_coord(coord: Coordinate, lat: bool) -> str:
    if lat:
        hems = ['S', 'N']
    else:
        hems = ['W', 'E']
    if isinstance(coord, float):
        return f"{abs(coord)}°{hems[coord >= 0]}"
    elif isinstance(coord[2], float):
        return f"{coord[1]}°{coord[2]}'{hems[coord[0]]}"
    else:
        return f"{coord[1]}°{coord[2][0]}'{coord[2][1]}''{hems[coord[0]]}"


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
            return (degrees >= 0, abs(degrees), minutes), tokens1
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
            return (not coord[0], coord[1], coord[2])


def parse_coordinates(string: str, lat_first: bool) -> Tuple[Coordinate, Coordinate]:
    """
    parses a string into coordinates with latitude first

    lat_first indicates whether latitude is first in unmarked strings

    if the whole string is not consumed, raises a ValueError with the rest
    """
    # sanitize the string
    string = prepare_string(string)
    # extract the quadrant information
    quadrant = [c for c in string if c in 'NSEW']
    # defines method orient that exchanges and negates the coordinates based on the quadrant
    if not quadrant:
        if lat_first:
            def orient(p: Tuple[Coordinate, Coordinate]
                       ) -> Tuple[Coordinate, Coordinate]:
                return p
        else:
            def orient(p: Tuple[Coordinate, Coordinate]
                       ) -> Tuple[Coordinate, Coordinate]:
                return (p[1], p[0])
    elif len(quadrant) == 2:
        if quadrant[0] in 'NS' and quadrant[1] in 'WE':
            def swap(p: Tuple[Coordinate, Coordinate]) -> Tuple[Coordinate, Coordinate]:
                return p
        elif quadrant[0] in 'WE' and quadrant[1] in 'NS':
            def swap(p: Tuple[Coordinate, Coordinate]) -> Tuple[Coordinate, Coordinate]:
                return (p[1], p[0])

        def orient(p: Tuple[Coordinate, Coordinate]) -> Tuple[Coordinate, Coordinate]:
            return swap((hemisphere_sign(quadrant[0], p[0]), hemisphere_sign(quadrant[1], p[1])))
    # split the string into tokens
    tokens = [(int(m.group(1)), m.group(2))
              for m in re.finditer(r'(-?\d+)([^\d-]*)', string)]
    # parse coordinates one after the other
    coord0, tokens1 = parse_coord(tokens)
    coord1, rest = parse_coord(tokens1)
    if rest:
        # incomplete parse: error
        raise ValueError(''.join(str(n)+sep for n, sep in rest))
    else:
        return orient((coord0, coord1))


def process_simpl(input: Iterator[str]) -> Iterator[str]:
    # by default latitude comes first
    lat_first = True
    # read the first line
    try:
        heading = next(input).casefold()
    except StopIteration:
        return
    # try to find 'lat' and 'lon' in the first line
    lat_ind = heading.find('lat')
    lon_ind = heading.find('lon')
    if lat_ind >= 0 and lon_ind >= 0:
        # first line in the heading
        lat_first = lat_ind <= lon_ind
        try:
            line = next(input)
        except StopIteration:
            return
    else:
        # first line is not special
        line = heading
    # yield the output heading
    both = "latlon" if lat_first else "lotlan"
    yield f"original_lat\toriginal_lon\toriginal_{both}\tlat_corr\tlon_corr\tlat_dec\tlon_dec\tlatlon_dec\tlat_sx\tlon_sx\tlatlon_sx"
    while True:
        # format the part of the output with the original information
        line = line.strip()
        part1, sep, part2 = line.partition('\t')
        if not part1 or not part2 or part1.isspace() or part2.isspace():
            original = f"\t\t{line}"
        elif lat_first:
            original = f"{part1}\t{part2}\t"
        else:
            original = f"{part2}\t{part1}\t"
        # try to parse the line, if it fails, output just the original
        try:
            lat, lon = parse_coordinates(line, lat_first)
        except ValueError:
            yield original + '\t' * 8
        # compose the output
        lat_corr = str_coord(lat, True)
        lon_corr = str_coord(lon, False)
        lat_dec = str_coord(dec_coord(lat), True)
        lon_dec = str_coord(dec_coord(lon), False)
        lat_sx = str_coord(sx_coord(lat), True)
        lon_sx = str_coord(sx_coord(lon), False)
        yield f"{original}\t{lat_corr}\t{lon_corr}\t{lat_dec}\t{lon_dec}\t{lat_dec} {lon_dec}\t{lat_sx}\t{lon_sx}\t{lat_sx} {lon_sx}"
        try:
            line = next(input)
        except StopIteration:
            break


for line in process_simpl(sys.stdin):
    print(line)

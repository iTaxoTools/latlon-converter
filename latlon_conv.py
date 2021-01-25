#!/usr/bin/env python3
import re
import os
import math
import sys
from typing import List, Tuple, Union, Iterator, Optional
import tkinter as tk
from tkinter import ttk
import tkinter.filedialog as tkfiledialog
import tkinter.messagebox
import tkinter.font as tkfont
import warnings

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
        return f"{abs(coord):.5f}{hems[coord >= 0]}"
    else:
        sign,degrees, minutes = coord
        if isinstance(minutes, float):
            return f"{degrees}°{minutes:.3f}'{hems[sign]}"
        else:
            return f"{degrees}°{minutes[0]}'{minutes[1]:.1f}''{hems[sign]}"


def signed_coord(coord: str) -> str:
    hem = coord[-1]
    if hem in 'SW':
        return '-' + coord[:-1]
    else:
        return coord[:-1]


def prepare_string(string: str) -> str:
    """
    standardizes the string

    raises ValueError if both 'O' or 'o' and '°' are present in the string
    """
    if ('O' in string or 'o' in string) and '°' in string:
        raise ValueError("Encountered 'O' to indicate geographical direction which can mean either West (Spanish/French/Italian) or East (German); please change to E or W before conversion.")
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
        return float(tokens[0][0]), tokens[1:]

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
        return float(tokens[0][0]), tokens[1:]

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
        return float(tokens[0][0]), tokens[1:]

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
    if c in 'ne':
        return coord
    else:
        if isinstance(coord, float):
            return -coord
        else:
            return (not coord[0], coord[1], coord[2])

def cannot_parse_error(tokens: Tokens) -> ValueError:
    """
    makes a ValueError
    "Cannot parse: tokens as str"
    """
    return ValueError("Cannot parse: " + ''.join(str(n)+sep for n, sep in tokens))

def parse_coordinates(string: str, lat_first: bool) -> Tuple[Coordinate, Coordinate]:
    """
    parses a string into coordinates with latitude first

    lat_first indicates whether latitude is first in unmarked strings

    if the whole string is not consumed, raises a ValueError with the rest
    """
    # sanitize the string
    string = prepare_string(string)
    # extract the quadrant information
    letters = [c for c in string if c.isalpha()]
    quadrant = [c for c in letters if c in 'nsew']
    if len(letters) > len(quadrant):
        # there are disallowed letters in coordinates
        raise ValueError("Letters {set(letters) - set(quadrant)} cannot be regognized as hemispheres")
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
        if quadrant[0] in 'ns' and quadrant[1] in 'we':
            def swap(p: Tuple[Coordinate, Coordinate]) -> Tuple[Coordinate, Coordinate]:
                return p
        elif quadrant[0] in 'we' and quadrant[1] in 'ns':
            def swap(p: Tuple[Coordinate, Coordinate]) -> Tuple[Coordinate, Coordinate]:
                return (p[1], p[0])

        def orient(p: Tuple[Coordinate, Coordinate]) -> Tuple[Coordinate, Coordinate]:
            return swap((hemisphere_sign(quadrant[0], p[0]), hemisphere_sign(quadrant[1], p[1])))
    else:
        raise ValueError(f"Cannot recognize the order of coordinates: {string}")
    # split the string into tokens
    tokens = [(int(m.group(1)), m.group(2))
              for m in re.finditer(r'(-?\d+)([^\d-]*)', string)]
    # parse coordinates one after the other
    try:
        coord0, tokens1 = parse_coord(tokens)
    except ValueError as ex:
        raise cannot_parse_error(tokens) from ex
    if not tokens1 and len(tokens) == 2: # probably the degrees, degrees situation
        return orient((float(tokens[0][0]), float(tokens[1][0])))
    try:
        coord1, rest = parse_coord(tokens1)
    except ValueError as ex:
        raise cannot_parse_error(tokens1) from ex
    if rest:
        # incomplete parse: error
        raise cannot_parse_error(rest)
    else:
        return orient((coord0, coord1))


def process_simpl(input: Iterator[str]) -> Iterator[List[str]]:
    # by default latitude comes first)
    lat_first = True
    # read the first line
    try:
        line = next(input)
        heading = line.casefold()
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
    # yield the output heading
    both = "latlon" if lat_first else "lotlan"
    yield ["original_lat", "original_lon", f"original_{both}", "lat_corr", "lon_corr", "lat_dec", "lon_dec", "latlon_dec", "lat_sx", "lon_sx", "latlon_sx", "Remark"]
    while True:
        # format the part of the output with the original information
        line = line.strip()
        part1, _, part2 = line.partition('\t')
        if not part1 or not part2 or part1.isspace() or part2.isspace():
            original = ["", "", line]
        elif lat_first:
            original = [part1, part2, ""]
        else:
            original = [part2, part1, ""]
        # try to parse the line, if it fails, output just the original
        try:
            lat, lon = parse_coordinates(line, lat_first)
        except ValueError as ex:
            yield original + [""] * 8 + [str(ex)]
            try:
                line = next(input)
            except StopIteration:
                break
            continue
        # compose the output
        lat_corr = str_coord(lat, True)
        lon_corr = str_coord(lon, False)
        lat_dec = str_coord(dec_coord(lat), True)
        lon_dec = str_coord(dec_coord(lon), False)
        lat_sx = str_coord(sx_coord(lat), True)
        lon_sx = str_coord(sx_coord(lon), False)
        yield original + [lat_corr, lon_corr, signed_coord(lat_dec), signed_coord(lon_dec), f"{lat_dec} {lon_dec}", lat_sx, lon_sx, f"{lat_sx} {lon_sx}", ""]
        try:
            line = next(input)
        except StopIteration:
            break


def launch_gui() -> None:
    # initialization
    root = tk.Tk()
    root.title("LatLonConverter")
    if os.name == "nt":
        root.wm_iconbitmap(os.path.join('data', 'LatLonIcon.ico'))
    mainframe = ttk.Frame(root, padding=5)
    root.rowconfigure(1, weight=1)
    root.columnconfigure(0, weight=1)
    mainframe.rowconfigure(4, weight=1)
    mainframe.columnconfigure(2, weight=1)

    style = ttk.Style()
    style.configure("ConvertButton.TButton", background="blue")

    # banner frame
    banner_frame = ttk.Frame(root)
    banner_img = tk.PhotoImage(file=os.path.join(
        "data", "iTaxoTools Digital linneaeus MICROLOGO.png"))
    banner_image = ttk.Label(banner_frame, image=banner_img)
    banner_image.grid(row=0, column=0, rowspan=2, sticky='nsw')
    program_name = ttk.Label(
        banner_frame, text="LatLonConverter", font=tkfont.Font(size=20))
    program_name.grid(row=1, column=1, sticky='sw')
    program_description = ttk.Label(
        banner_frame, text="A batch converter of geographical coordinates")
    program_description.grid(row=1, column=2, sticky='sw', ipady=4, ipadx=15)
    banner_frame.grid(column=0, row=0, sticky='nsw')


    # create labels
    infile_lbl = ttk.Label(mainframe, text="Input file")
    outfile_lbl = ttk.Label(mainframe, text="Output file")

    # create entries
    infile_var = tk.StringVar()
    infile_entr = ttk.Entry(mainframe, textvariable=infile_var)
    outfile_var = tk.StringVar()
    outfile_entr = ttk.Entry(mainframe, textvariable=outfile_var)

    # create texts
    input_frame = ttk.Frame(mainframe)
    input_frame.rowconfigure(1, weight=1)
    input_frame.columnconfigure(0, weight=1)
    input_text = tk.Text(input_frame, width=50, height=15)
    input_lbl = ttk.Label(input_frame, text="Paste coordinates here for fast conversion into decimal format\n(one pair of coordinates per line, in any format)")
    input_xscroll = ttk.Scrollbar(
        input_frame, orient=tk.HORIZONTAL, command=input_text.xview)
    input_yscroll = ttk.Scrollbar(
        input_frame, orient=tk.VERTICAL, command=input_text.yview)
    input_text.configure(xscrollcommand=input_xscroll.set,
                         yscrollcommand=input_yscroll.set)
    input_lbl.grid(row=0, column=0, sticky='w')
    input_text.grid(row=1, column=0, sticky='nsew')
    input_xscroll.grid(row=2, column=0, sticky='nsew')
    input_yscroll.grid(row=1, column=1, sticky='nsew')

    output_frame = ttk.Frame(mainframe)
    output_frame.rowconfigure(1, weight=1)
    output_frame.columnconfigure(0, weight=1)
    output_text = tk.Text(output_frame, width=50, height=15, wrap='none')
    output_lbl = ttk.Label(output_frame, text="If the data have been pasted into the window on the left,\nthe converted output will be show here.")
    output_xscroll = ttk.Scrollbar(
        output_frame, orient=tk.HORIZONTAL, command=output_text.xview)
    output_yscroll = ttk.Scrollbar(
        output_frame, orient=tk.VERTICAL, command=output_text.yview)
    output_text.configure(xscrollcommand=output_xscroll.set,
                          yscrollcommand=output_yscroll.set)
    output_lbl.grid(row=0, column=0, sticky='w')
    output_text.grid(row=1, column=0, sticky='nsew')
    output_xscroll.grid(row=2, column=0, sticky='nsew')
    output_yscroll.grid(row=1, column=1, sticky='nsew')

    # internal functions
    def input_lines() -> Iterator[str]:
        """
        returns an iterator over the input lines

        if the input file name is given, the line comes from it,
        otherwise from the input text widget
        """
        filename = infile_var.get()
        if filename and not filename.isspace():
            with open(filename, errors='replace') as file:
                for line in file:
                    yield line
        else:
            text = input_text.get('1.0', 'end')
            for line in text.splitlines():
                yield line

    def write_output(lines: Iterator[List[str]]) -> None:
        """
        writes the output

        if the output file name is given, the output is written to it,
        otherwise to the output text widget
        """
        filename = outfile_var.get()
        output_text.delete('1.0', 'end')
        if filename and not filename.isspace():
            with open(filename, mode='w') as file:
                for line in lines:
                    print("\t".join(line), file=file)
        else:
            for line in lines:
                output_text.insert('end', f"{line[5]}\t{line[6]}\t{line[-1]}")
                output_text.insert('end', '\n')

    def browse_infile() -> None:
        newpath: Optional[str] = tkfiledialog.askopenfilename()
        if (newpath):
            try:
                newpath = os.path.relpath(newpath)
            except:
                newpath = os.path.abspath(newpath)
            infile_var.set(newpath)

    def browse_outfile() -> None:
        newpath: Optional[str] = tkfiledialog.asksaveasfilename()
        if (newpath):
            try:
                newpath = os.path.relpath(newpath)
            except:
                newpath = os.path.abspath(newpath)
            outfile_var.set(newpath)

    def process() -> None:
        """
        command for the Process button
        """
        try:
            # catch all warnings
            with warnings.catch_warnings(record=True) as warns:
                write_output(process_simpl(input_lines()))
                # display the warnings generated during the conversion
                for w in warns:
                    tkinter.messagebox.showwarning("Warning", str(w.message))
            # notify the user that the converions is finished
            tkinter.messagebox.showinfo(
                "Done.", "The processing has been completed")
        # show the ValueErrors and FileNotFoundErrors
        except ValueError as ex:
            tkinter.messagebox.showerror("Error", str(ex))
        except FileNotFoundError as ex:
            tkinter.messagebox.showerror("Error", str(ex))

    def load() -> None:
        """
        loads the text from the input file into the input text widget
        """
        filename = infile_var.get()
        input_text.delete('1.0', 'end')
        if filename and not filename.isspace():
            with open(filename, errors='replace') as file:
                for line in file:
                    input_text.insert('end', line)

    # create buttons
    infile_btn = ttk.Button(mainframe, text="Browse", command=browse_infile)
    outfile_btn = ttk.Button(mainframe, text="Browse", command=browse_outfile)
    load_btn = ttk.Button(mainframe, text="Load", command=load)
    process_btn = ttk.Button(mainframe, text="Convert", command=process, style="ConvertButton.TButton")

    # display the widgets
    infile_lbl.grid(row=0, column=0, sticky='w')
    infile_entr.grid(row=1, column=0, sticky='we')
    infile_btn.grid(row=1, column=1, sticky='w')

    outfile_lbl.grid(row=0, column=3, sticky='w')
    outfile_entr.grid(row=1, column=3, sticky='we')
    outfile_btn.grid(row=1, column=4, sticky='w')

    load_btn.grid(row=2, column=0)
    process_btn.grid(row=2, column=2)

    ttk.Separator(mainframe, orient='horizontal').grid(row=3, column=0, columnspan=5, sticky='nsew', pady=20)

    input_frame.grid(row=4, column=0, columnspan=2)
    output_frame.grid(row=4, column=3, columnspan=2)

    ttk.Separator(root, orient='horizontal').grid(row=1, column=0, sticky='nsew')

    mainframe.grid(row=2, column=0, sticky='nsew')

    root.mainloop()


if '--cmd' in sys.argv:
    for line in process_simpl(sys.stdin):
        print('\t'.join(line))
else:
    launch_gui()

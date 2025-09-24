#!/usr/bin/env python3
from collections import defaultdict
import os
import sys
import csv
from optparse import OptionParser
import numpy
import pylab
from matplotlib import style
style.use("bmh")

parser = OptionParser()
parser.add_option("--ylimit-up", dest="y_up",
                  default=None, help="Y axis upper limts")
parser.add_option("--ylimit-down", dest="y_down",
                  default=None, help="Y axis lower limits")
parser.add_option("--xlimit-up", dest="x_up",
                  default=None, help="X axis upper limts")
parser.add_option("--xlimit-down", dest="x_down",
                  default=None, help="X axis lower limits")
parser.add_option("-d", "--csv-separator", dest="csv_sep",
                  default=";", help="Separator for csv file.")
parser.add_option("-f", "--data-file", dest="data_file",
                  default=None, help="Data file")
parser.add_option("-n", "--module-max", dest="module_max", action="store_true",
                  default=False, help="Plot normalizided samples.")

parser.add_option("-m", "--show-limits-lines", dest="limit_line", nargs=2, type="float",
                  default=[], help="Plot limit horizontal lines.")

parser.add_option("-t", "--traspone-lines", dest="traspone_lines", default=False,
                  action="store_true", help="Traspone input lines, invert row with column")

parser.add_option("-s", "--show-limits", dest="show_limits",
                  action="store_true", default=False,
                  help="Show avg and sigma limtis on gaussian curve")

parser.add_option("-x", "--x-series", dest="x_series", default=None,
                  help="Column for x axis.")

parser.add_option("-a", "--filter-head", dest="filter_head", default=None,
                  help="Select column by header name")

parser.add_option("-c", "--filter-col", dest="filter_col", default=None,
                  help="Skip line with col > filter_col")

parser.add_option("--only-extra", dest="only_extra_column", default=False,
                  action="store_true",
                  help="Show only extra computed column")

parser.add_option("-k", "--scatter-plot", dest="scatter_plot",
                  action="store_true",
                  default=False,
                  help="Show scatter plot")

parser.add_option("--py-data", dest="py_row_data",
                  default=None,
                  help="Get data from python data array")

(options, args) = parser.parse_args()



select = False
if args:
    select = True


PROCESS = {
    # 0: lambda x: x*1/60,
    # 4: lambda x: x*100,
    # 5: lambda x: x*100,
    # 1: 1/9.8,
    # 2: 1/9.8,
    # 3: 1/9.8,
    # 6: lambda x: x*1.9,
    # 5: lambda x: x*2.5,
}

hdr = []
data = defaultdict(list)
if options.traspone_lines:
    data = []

def fix(v, ncol):
    try:
        if type(v) != float:
            v = v.replace(',', '.')
        v = float(v)
        if ncol in PROCESS:
            v = PROCESS[ncol](v)
    except ValueError as e:
        #print(">>>", v, e)
        return None
    except TypeError as e:
        #print(">>>", v, e)
        return None

    return v

if options.py_row_data is not None:
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("raw_data", options.py_row_data)
        raw_data = importlib.util.module_from_spec(spec)
        sys.modules["raw_data"] = raw_data
        spec.loader.exec_module(raw_data)
    except ImportError as e:
        print("Missing python file rawdata.py: ", e)

        print(parser.print_help())
        sys.exit(1)

    idx = 0
    for m in dir(raw_data):
        if m.startswith("_"):
            continue
        d = getattr(raw_data, m)
        hdr.append(m)
        data[idx] = [fix(i, idx) for i in d]
        idx += 1

if options.data_file is None and options.py_row_data is None:
    print(f"{sys.argv[0]} -f <file.csv> [colum]")
    print(parser.print_help())
    sys.exit(1)

if options.data_file is not None and options.py_row_data is None:
    with open(options.data_file, newline='') as csvfile:
        for row in csv.reader(csvfile, delimiter=options.csv_sep):
            if options.traspone_lines:
                hdr.append(row[0])
                print(row[0])
                l = list()
                for n, v in enumerate(row):
                    v = fix(v, n)
                    if v is not None:
                        l.append(v)
                data.append(l)
            else:
                if not hdr:
                    print(row)
                    hdr = row
                for n, v in enumerate(row):
                    v = fix(v, n)
                    if v is not None:
                        data[n].append(v)

plot_col = range(len(data))
if select:
    plot_col = map(int, args)

plot_col = list(plot_col)


def pulse_width(c, th=100, tl=50, scale=1.0, peak_max=1000.0):
    st = False
    count = 0
    v = 0
    diffs = []
    for i in c:
        v = 0
        if i <= tl and not st:
            st = True
            count = 0
        if i > th and st:
            st = False
            v = min(count/scale, peak_max/scale)
        if st:
            count += 1
        diffs.append(v)

    #print(f"<0.5:{len(list(filter(lambda x: x <= 0.5, df)))}")
    #print(f">0.5:{len(list(filter(lambda x: x > 0.5 and x < 1.1, df)))}")
    #print(f"<2:{len(list(filter(lambda x: x > 1.1 and x < 2, df)))}")
    return diffs


EXTRA = {
    # 5: pulse_width,
    #5: (pulse_width, "Off det.")
}

extra_colum = []
last_column = len(data)
count = 0
for m in range(last_column):
    if not data[m]:
        continue
    if m in EXTRA:
        callback, extra_colum_label = EXTRA[m]
        data[last_column+count] = callback(data[m],
                                           th=1.1, tl=0.5, scale=100)
        extra_colum.append(last_column+count)
        plot_col.append(last_column+count)
        hdr.append(f"{extra_colum_label}#{last_column+count}")
        count += 1

label_hand = []
raw_data = []
for n, m in enumerate(plot_col):
    if not data[m]:
        continue

    skip_col = False
    if options.filter_head is not None:
        for i in options.filter_head.split(" "):
            skip_col = True
            if i in hdr[m]:
                print(hdr[m], options.filter_head)
                skip_col = False
                break
    if skip_col:
        continue

    label = f"C{m}"
    if hdr:
        try:
            label = f"{hdr[m]}"
        except IndexError:
            pass

    avg = numpy.mean(data[m])
    sigma = numpy.std(data[m], axis=0)
    s2 = sigma * sigma
    s_min = min(data[m])
    s_max = max(data[m])
    rms = numpy.sqrt(sum([x * x for x in data[m]]) / len(data[m]))

    lw_width = '3'
    ls_style = '-'
    if m in extra_colum:
        lw_width = '2'
        ls_style = ':'

    if options.only_extra_column:
        if m in extra_colum:
            raw_data = data[m]
    else:
        raw_data = data[m]

    if options.module_max:
        raw_data = [(x - s_min) / (s_max - s_min)
                    for x in data[m]]

    print(f"Col[{m:5d}] min[{s_min:8.5f}] max[{s_max:8.5f}] sg[{sigma:8.5f}]"
          "rms[{rms: 8.5f}] avg[{avg: 8.5f}] Nomal[{options.module_max}]")

    title = options.data_file
    if options.data_file is None:
        title = options.py_row_data
    pylab.title(f"{os.path.basename(title)}")


    # Plot raw data
    l = None
    if options.x_series is not None:
        pylab.title(f"{options.data_file}")
        x_ser = int(options.x_series)
        if x_ser > len(data):
            print("Wrong column num for x axie.")
            sys.exit(1)
        pylab.xlabel(hdr[x_ser])
        n = min(len(data[x_ser]), len(raw_data))

        if options.scatter_plot:
            l = pylab.scatter(data[x_ser][:n], raw_data[:n], s=[12], marker='x', label=label)
        else:
            l, = pylab.plot(data[x_ser][:n], raw_data[:n], ls=ls_style, lw=lw_width, label=label)
    else:
        if options.scatter_plot:
            l = pylab.scatter(raw_data, raw_data[:n], s=[12], marker='x', label=label)
        else:
            l, = pylab.plot(raw_data, ls=ls_style, lw=lw_width, label=label)

    label_hand.append(l)

if options.x_up is not None:
    pylab.xlim(xmax=float(options.x_up))
if options.x_down is not None:
    pylab.xlim(xmin=float(options.x_down))

if options.y_up is not None:
    pylab.ylim(ymax=float(options.y_up))
if options.y_down is not None:
    pylab.ylim(ymin=float(options.y_down))


pylab.grid(which='major', color='#666666', linestyle='-')
pylab.minorticks_on()
pylab.grid(which='minor', color='#999999', linestyle='-', alpha=0.2)

for lmt in options.limit_line:
    pylab.axhline(y=lmt, color='r', linestyle='-')

# pylab.axhline(y=100, color='b', linestyle=':')
# pylab.axhline(y=200, color='g', linestyle=':')
# pylab.axhline(y=300, color='grey', linestyle=':')

#pylab.tight_layout()
pylab.legend(loc='upper left', bbox_to_anchor=(0.75, 1), fancybox=True)
pylab.show()


import drawSvg as draw
import csv
import argparse
import ast
import os

#############################
## Argument handling
#############################

parser = argparse.ArgumentParser(description='This script will generate nice dashboard with link to C sources or execution logs, as well as the actual result. It takes a csv as input and generate both a svg and png')


parser.add_argument('-i', metavar='input', default='result.csv', help='the input csv file containing all the data generated from our runner.')

parser.add_argument('-o', metavar='output', default='out', type=str, help='name of the file that will be generated (both output.svg and output.png)')

parser.add_argument('--header', metavar='header', default=True, type=bool, help='wether the input csv contains an header')

args = parser.parse_args()
    
#############################
## Specific SVG class
#############################

    
class Hyperlink(draw.DrawingParentElement):
    TAG_NAME = 'a'
    def __init__(self, href, target=None, **kwargs):
        super().__init__(href=href, target=target, **kwargs)

class Image(draw.DrawingBasicElement):
    TAG_NAME = 'image'
    def __init__(self, x, y, width, height, href, **kwargs):
        try:
            y = -y-height
        except TypeError:
            pass
        super().__init__(x=x, y=y, width=width, height=height, href=href, **kwargs)

class Group(draw.DrawingDef):
    TAG_NAME = 'g'
    def __init__(self, ids, **kwargs):
        super().__init__(id=ids, **kwargs)

        
#############################
## GLOBAL CONSTANT
#############################

WIDTH = 900
HEIGHT = 1200
HEADER_SIZE = 15


#############################
## Handling CSV
#############################

csvread = []
with open(args.i, newline='') as result_file:
    csvread = csv.reader(result_file, delimiter=';')
    isHeader = args.header
    data = []
    for row in csvread:
        if isHeader:          
            header = row
        else:
            data.append(row)
        isHeader = False

d = draw.Drawing(WIDTH, HEIGHT, origin='center', displayInline=True)

#############################
## Data dependant constant
#############################


tools = list(set([row[2] for row in data]))
tools.sort()

width_per_tool = WIDTH / (len(tools))

error_type_not_sorted = list(set([row[6] for row in data]))
error_type_not_sorted.sort()
error_type = ['OK'] + [error for error in error_type_not_sorted if error != 'OK'] 


height_per_error = HEIGHT / (len(error_type) + 1)

nb_uniq_testcase = len([R for R in data if R[2]==tools[0]])

CASE_HEIGHT = HEIGHT / (((nb_uniq_testcase // 5)*1.1 + len(error_type)*2 + 1))
CASE_WIDTH = width_per_tool / (5.7)

case_per_error = []
for error in error_type:
    case_per_error.append([row for row in data if row[6] == error])

nb_error_type = {}

nb_FP = {}
nb_TP = {}
nb_TN = {}
nb_FN = {}
nb_error = {}

for t in tools:
    nb_FP[t] = 0
    nb_TP[t] = 0
    nb_TN[t] = 0
    nb_FN[t] = 0
    nb_error[t] = 0
    

#############################
## Actual printing method
#############################

def print_result(top_left_x, top_left_y, i, j, row):


    name = row[0]
    id = row[1]
    tool = row[2]
    to = row[3]
    np = row[4]
    buf = row[5]
    expected = row[6]
    result = row[7]
    elapsed = row[8]

    link = "https://gitlab.com/MpiCorrectnessBenchmark/mpicorrectnessbenchmark/-/tree/master/codes/{}.c".format(name)
    
    r = Hyperlink(link)
    
    fig = "tick.svg"
    
    if result == "timeout":
        fig = "TO.svg"
        nb_error[tool] += 1
    elif result == "UNIMPLEMENTED":
        fig = "CUN.svg"
        nb_error[tool] += 1
    elif result == "failure":
        fig = "RSF.svg"
        nb_error[tool] += 1

    elif expected == 'OK':
        if result == 'OK':
            fig = "tick.svg"
            nb_TN[tool] += 1
        else:
            fig = "cross.svg"
            nb_FP[tool] += 1
    elif expected == 'ERROR':
        if result == 'OK':
            fig = "cross.svg"
            nb_FN[tool] += 1
        else:
            fig = "tick.svg"
            nb_TP[tool] += 1

    r.append(draw.Image(top_left_x + 0.1*CASE_WIDTH + i * (CASE_WIDTH*1.1),
            top_left_y - 0.1*CASE_HEIGHT - j * (CASE_HEIGHT*1.1),
            CASE_WIDTH,
            CASE_HEIGHT,
            fig,
            embed=True))

    r.append(draw.Rectangle(top_left_x + 0.1*CASE_WIDTH + i * (CASE_WIDTH*1.1),
            top_left_y - 0.1*CASE_HEIGHT - j * (CASE_HEIGHT*1.1),
            CASE_WIDTH,
            CASE_HEIGHT,
            fill='none',
            stroke="black",
            stroke_width="0.2"
    ))
    
    desc = "TEST : " + tool + " np=" + np + " to=" + to
    if buf != 'NA':
        desc += " buf=" + buf
    desc += " " + name

    desc += "\nEXPECTED : " + expected[0]

    if result == 'CUN': 
        desc += "\nRETURNED : Compilation Failure"  
    elif result == 'RSF':
        desc += "\nRETURNED : Runtime Failure"  
    else :
        desc += "\nRETURNED : " + result  
        
    r.append(draw.Title(desc))

    if tool == tools[0]:
        expects = expected[0]
        if not expects in nb_error_type:
            nb_error_type[expects] = 1
        else:
            nb_error_type[expects] += 1
    
    return r

    
#############################
## Going throught data
#############################


for i in range(len(tools)):
    name = ""
    if tools[i]=="aislinn":
        name = "Aislinn"
    if tools[i]=="isp":
        name = "ISP"
    if tools[i]=="civl":
        name = "CIVL"
    if tools[i]=="parcoach":
        name = "Parcoach"
    if tools[i]=="must" or tools[i]=="mustdist":
        name = "MUST"
    if tools[i]=="simgrid":
        name = "McSimGrid"
        
    d.append(draw.Text(name, HEADER_SIZE+5, -(WIDTH/2) + (i)*width_per_tool + 5,  (HEIGHT/2) - 20, fill='black'))


adjust_height = 70
    
for i in range(len(error_type)):

    # Print the error name
    d.append(draw.Text(error_type[i], HEADER_SIZE-2, -(WIDTH/2) + 5,  (HEIGHT/2) - adjust_height + 25, fill='black'))
    
    
    for j in range(len(tools)):
        
        to_print = [cases for cases in case_per_error[i] if cases[2]==tools[j]]
        to_print.sort()
        
        for k in range(len(to_print)):
            row = to_print[k]
            d.append(print_result(-(WIDTH/2) + (j)*width_per_tool,
                                  (HEIGHT/2) - adjust_height,
                                  k%5,
                                  k//5,
                                  row))

    to_add = len(to_print)//5
    if len(to_print)%5!=0:
        to_add+=1
    adjust_height += (to_add)*CASE_HEIGHT*1.1
    adjust_height += 30
          


d.setPixelScale(2)  # Set number of pixels per geometry unit
#d.setRenderSize(400,200)  # Alternative to setPixelScale

d.saveSvg(args.o + '.svg')
d.savePng(args.o + '.png')


#############################
## Generating the caption
#############################

caption = draw.Drawing(CASE_WIDTH*15, CASE_HEIGHT*10, displayInline=True)

x = 10
y = CASE_HEIGHT*10 - 20

caption.append(draw.Image(x, y, CASE_WIDTH, CASE_HEIGHT, "tick.svg", embed=True))

caption.append(draw.Rectangle(x, y, CASE_WIDTH, CASE_HEIGHT,
            fill='none',
            stroke="black",
            stroke_width="0.2"
    ))

caption.append(draw.Text("Right", HEADER_SIZE, x + 1.5*CASE_WIDTH, y, fill='black'))

y -= CASE_HEIGHT*1.5

caption.append(draw.Image(x,
                    y,
                    CASE_WIDTH,
                    CASE_HEIGHT,
                    "cross.svg",
                    embed=True))

caption.append(draw.Rectangle(x,
                              y,
                              CASE_WIDTH, CASE_HEIGHT,
                              fill='none',
                              stroke="black",
                              stroke_width="0.2"))

caption.append(draw.Text("Wrong", HEADER_SIZE, x + 1.5*CASE_WIDTH, y, fill='black'))

y -= CASE_HEIGHT*1.5

caption.append(draw.Image(x,
                    y,
                    CASE_WIDTH,
                    CASE_HEIGHT,
                    "TO.svg",
                    embed=True))

caption.append(draw.Rectangle(x,
                              y,
                              CASE_WIDTH, CASE_HEIGHT,
                              fill='none',
                              stroke="black",
                              stroke_width="0.2"))

caption.append(draw.Text("Time Out", HEADER_SIZE, x + 1.5*CASE_WIDTH, y, fill='black'))

y -= CASE_HEIGHT*1.5

caption.append(draw.Image(x,
                    y,
                    CASE_WIDTH,
                    CASE_HEIGHT,
                    "CUN.svg",
                    embed=True))

caption.append(draw.Rectangle(x,
                              y,
                              CASE_WIDTH, CASE_HEIGHT,
                              fill='none',
                              stroke="black",
                              stroke_width="0.2"))

caption.append(draw.Text("Unsupported feature", HEADER_SIZE, x + 1.5*CASE_WIDTH, y, fill='black'))

y -= CASE_HEIGHT*1.5

caption.append(draw.Image(x,
                    y,
                    CASE_WIDTH,
                    CASE_HEIGHT,
                    "RSF.svg",
                    embed=True))

caption.append(draw.Rectangle(x,
                              y,
                              CASE_WIDTH, CASE_HEIGHT,
                              fill='none',
                              stroke="black",
                              stroke_width="0.2"))

caption.append(draw.Text("Run time error", HEADER_SIZE, x + 1.5*CASE_WIDTH, y, fill='black'))

caption.saveSvg('caption.svg')

#############################
## Printing result
#############################

for t in tools:
    print("TOOLS : {}\n  TP : {}\n  TN : {}\n  FP : {}\n  FN : {}\n  Error : {}\n".
          format(t, nb_TP[t], nb_TN[t], nb_FP[t], nb_FN[t], nb_error[t]))

if 'aislinn' in tools and 'isp' in tools and 'civl' in tools and 'must' in tools and 'parcoach' in tools and 'simgrid' in tools:
    print("Aislinn & {} & {} & {} & {} & {} \\\\\n CIVL & {} & {} & {} & {} & {} \\\\\n ISP & {} & {} & {} & {} & {} \\\\\n Must & {} & {} & {} & {} & {}\\\\\n Parcoach & {} & {} & {} & {} & {}\\\\\n McSimGrid & {} & {} & {} & {} & {}\\\\".format(nb_TP['aislinn'], nb_FN['aislinn'], nb_FP['aislinn'], nb_TN['aislinn'], nb_error['aislinn'],
    nb_TP['civl'], nb_FN['civl'], nb_FP['civl'], nb_TN['civl'], nb_error['civl'],
    nb_TP['isp'], nb_FN['isp'], nb_FP['isp'], nb_TN['isp'], nb_error['isp'],
    nb_TP['must'], nb_FN['must'], nb_FP['must'], nb_TN['must'], nb_error['must'],
    nb_TP['parcoach'], nb_FN['parcoach'], nb_FP['parcoach'], nb_TN['parcoach'], nb_error['parcoach'],
    nb_TP['simgrid'], nb_FN['simgrid'], nb_FP['simgrid'], nb_TN['simgrid'], nb_error['simgrid']))

#############################
## Extracting features
#############################

feature_data = [["Name", "Origin", "P2P", "iP2P", "PERS", "COLL", "iCOLL", "TOPO", "IO", "RMA", "PROB",
	 "COM", "GRP", "DATA", "OP", "LOOP", "SP", "deadlock", "numstab", "segfault", "mpierr",
	 "resleak", "livelock", "datarace"]]
directory = "../codes/"
for filename in os.listdir(directory):
    if filename.endswith(".c"):
        row = [0]*len(feature_data[0])
        row[0] = filename
        f = open(os.path.join(directory, filename), 'r')
        line = f.readline()
        while line[0] == "/":
            line = f.readline()
            parsed_line = line.split(" ")
            try:
                if len(parsed_line) >= 3:
                    index_data = feature_data[0].index(parsed_line[1][:-1])
                    if parsed_line[1][:-1] == "Origin":
                        row[index_data] = parsed_line[2].rstrip('\n')
                    else:
                        row[index_data] = parsed_line[2][:1]
            except ValueError:
                pass
        f.close()
        feature_data.append(row)

feature_per_file = {}
for row in feature_data:
    feature_per_file[row[0]] = []
    if "no-error" in row[0]:
        for j in range(2,17):
            if row[j] == "C":
                feature_per_file[row[0]].append(feature_data[0][j]) 
    else:
        for j in range(2,17):
            if row[j] == "I":
                feature_per_file[row[0]].append(feature_data[0][j])
        if len(feature_per_file[row[0]]) == 0:
            for j in range(2,17):
                if row[j] == "C":
                    feature_per_file[row[0]].append(feature_data[0][j])
        
                
most_feature_per_file = 0
for filename in feature_per_file:
    feature_per_file[filename].sort()
    most_feature_per_file = max(most_feature_per_file,
                                len(feature_per_file[filename]))


CASE_WIDTH = WIDTH / 5.7
width_per_feature = CASE_WIDTH / most_feature_per_file
CASE_HEIGHT = HEIGHT / ((nb_uniq_testcase // 5)*1.1 + len(error_type)*2 + 1)


nb_features = {}
for feat in ["P2P", "iP2P", "PERS", "COLL", "iCOLL", "TOPO", "IO", "RMA", "PROB", "COM", "GRP", "DATA", "OP", "LOOP", "SP"]:
    nb_features[feat] = [0,0]
    
#############################
## Feature printing function
#############################



def print_feature(top_left_x, top_left_y, i, j, n, feature):

    fig = "./featureFigs/{}.svg".format(feature)
    
    r = draw.Image(
        top_left_x + 0.1*CASE_WIDTH + i * (CASE_WIDTH*1.1) + n * width_per_feature,
        top_left_y - 0.1*CASE_HEIGHT - j * (CASE_HEIGHT*1.1),
        width_per_feature,
        CASE_HEIGHT,
        fig,
        embed=True)
    
    return r

def print_box(top_left_x, top_left_y, i, j):

    r = (draw.Rectangle(top_left_x + 0.1*CASE_WIDTH + i * (CASE_WIDTH*1.1),
            top_left_y - 0.1*CASE_HEIGHT - j * (CASE_HEIGHT*1.1),
            CASE_WIDTH,
            CASE_HEIGHT,
            fill='none',
            stroke="black",
            stroke_width="0.3"
    ))
    
    return r
    
#############################
## Printing features
#############################

feature_drawing = draw.Drawing(WIDTH, HEIGHT, origin='center', displayInline=True)

# for i in range(most_feature_per_file):
#     feature_drawing.append(draw.Text("Feature {}".format(i+1), HEADER_SIZE, -(WIDTH/2) + (i+1)*width_per_tool,  (HEIGHT/2) - 15, fill='black'))


adjust_height = 50
    
for i in range(len(error_type)):

    # Print the error name
    feature_drawing.append(draw.Text(error_type[i], HEADER_SIZE, -(WIDTH/2) + 5,  (HEIGHT/2) - adjust_height + 30, fill='black'))

    to_print = [cases for cases in case_per_error[i] if cases[2]==tools[0]]
    to_print.sort()
    
    for k in range(len(to_print)):

        filename = to_print[k][0] + '.c'

        if not filename in feature_per_file:
            continue
        
        list_feature = feature_per_file[filename]

        feature_drawing.append(print_box(-(WIDTH/2),
                                         (HEIGHT/2) - adjust_height,
                                         k%5,
                                         k//5))

        
        for j in range(len(list_feature)):
                       
            if j < len(feature_per_file[filename]):

                #counting
                if "no-error" in filename:
                    nb_features[list_feature[j]][0] += 1
                else:
                    nb_features[list_feature[j]][1] += 1

                #printing
                feature_drawing.append(print_feature(-(WIDTH/2),
                                                     (HEIGHT/2) - adjust_height,
                                                     k%5,
                                                     k//5,
                                                     j,
                                                     list_feature[j]))

    to_add = len(to_print)//5
    if len(to_print)%5!=0:
        to_add+=1
    adjust_height += (to_add)*CASE_HEIGHT*1.1
    adjust_height += 30

d.setPixelScale(2)  # Set number of pixels per geometry unit
#d.setRenderSize(400,200)  # Alternative to setPixelScale

feature_drawing.saveSvg('features.svg')
feature_drawing.savePng('features.png')

#############################
## Printing feature count
#############################

for feat in nb_features:
    print("FEATURE : {}\n  Correct : {}\n  Incorect : {}\n".
          format(feat, nb_features[feat][0], nb_features[feat][1]))


#############################
## Printing error count
#############################

for error in nb_error_type:
    print("ERROR : {}\n  Number : {}\n".
          format(error, nb_error_type[error]))


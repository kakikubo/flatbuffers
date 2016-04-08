import os
import sys
import re
import codecs
import subprocess
import shutil
import argparse
import json
import xlrd
from collections import OrderedDict
from logging import info, warning, debug
from PIL import Image

def merge_spine_animation_one(src_json, add_json, output_file):
    if src_json.has_key("animations") and add_json.has_key("animations"):
        src_animations = src_json["animations"]
        add_animations = add_json["animations"]
        for k, v in add_animations.items():
            #if not src_animations.has_key(k):
            src_animations[k] = v
            # print "add {0}".format(k)

    with open(output_file, 'w') as data:
        dump = json.dumps(src_json, ensure_ascii = False)
        data.write(dump.encode("utf-8"))

def merge_spine_animation(xls_file, sheet_name, start_row, column_label, input_file_dir, output_file_dir):
    index_row = int(start_row)
    index_col = -1
    book = xlrd.open_workbook(xls_file)
    sheet = book.sheet_by_name(sheet_name)
    if sheet.nrows > 0:
        for col in range(sheet.ncols):
            if sheet.cell_value(0, col) == column_label:
                index_col = col
                debug("find {0}:{1}".format(column_label, col))
                break
    if index_col < 0:
        return False

    add_json = {}
    for row in range(sheet.nrows):
        if (row < index_row):
            continue

        spine_ext = ".json"
        model_id = int(sheet.cell_value(row, 0))
        model_base = os.path.abspath(input_file_dir) + "/" + str(model_id) + spine_ext
        model_field = os.path.abspath(input_file_dir) + "/" + sheet.cell_value(row, index_col) + spine_ext
        output_file = os.path.abspath(output_file_dir) + "/" + str(model_id) + spine_ext

        #print "{0}+{1}->{2}".format(model_base, model_field, output_file)

        src_json = {}
        with open(model_base, 'r') as data:
            src_json = json.loads(data.read(), object_pairs_hook=OrderedDict)

        if not add_json.has_key(model_field):
            with open(model_field, 'r') as data:
                #print "open {0}".format(model_field)
                add_json[model_field] = json.loads(data.read(), object_pairs_hook=OrderedDict)

        merge_spine_animation_one(src_json, add_json[model_field], output_file)

# ---
# main function
#
if __name__ == '__main__':
    sys.stdout = codecs.lookup('utf_8')[-1](sys.stdout)
    parser = argparse.ArgumentParser(description='merge spine files', epilog="""\
example:
    $ ./merge_spine.py xls_file, sheet_name, start_row, column_label, input_file_dir, output_file_dir""")

    parser.add_argument('xls_file', help='excel file')
    parser.add_argument('sheet_name', help='sheet name in excel file')
    parser.add_argument('start_row', help='start row in sheet')
    parser.add_argument('column_label', help='column label in sheet')
    parser.add_argument('input_file_dir', help='input files dir')
    parser.add_argument('output_file_dir', help='output files dir')
    args = parser.parse_args()

    xls_file        = os.path.normpath(args.xls_file)
    sheet_name      = args.sheet_name
    start_row       = args.start_row
    column_label    = args.column_label
    input_file_dir  = os.path.normpath(args.input_file_dir)
    output_file_dir = os.path.normpath(args.output_file_dir)

    print "xls_file = {0}".format(xls_file)
    print "sheet_name = {0}".format(sheet_name)
    print "start_row = {0}".format(start_row)
    print "column_label = {0}".format(column_label)
    print "input_file_dir = {0}".format(input_file_dir)
    print "output_file_dir = {0}".format(output_file_dir)

    merge_spine_animation(xls_file, sheet_name, start_row, column_label, input_file_dir, output_file_dir)

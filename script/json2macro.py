#! /usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import codecs
import json
import re
import argparse
import logging
from logging import info, warning, error
from collections import OrderedDict

def upper_camel_case(s):
    return s[0:1].upper() + s[1:]

def generate_macro(data):
    s = "// generated by json2macro.py\n\n"

    for sheet in data:
        if re.match('json', sheet['srcType']):
            continue
        macro = "MASTER_GET" if sheet['srcType'] == 'object' else "MASTER_GET_V"
        s += macro+"("+upper_camel_case(sheet['name'])+', '+sheet['name']+")\n"

    return s

# ---
# root function
#
def json2fbs(input_json, output_h, key):
    with open(input_json, 'r') as f:
        data = json.load(f, object_pairs_hook=OrderedDict)
        s = generate_macro(data[key])
        with open(output_h, 'w') as f:
            f.write(s)

# ---
# main function
#
if __name__ == '__main__':
    sys.stdout = codecs.lookup('utf_8')[-1](sys.stdout)
    logging.basicConfig(level = logging.INFO, format = '%(asctime)-15s %(levelname)s %(message)s')
    parser = argparse.ArgumentParser(description = 'generate accessor macro header file from json')
    parser.add_argument('input_json', metavar = 'input.json', help = 'input sheet definition data json file')
    parser.add_argument('output_h',   metavar = 'output.h',   help = 'output macro header file')
    parser.add_argument('--key',      default = 'sheet',      help = 'root node of macro generate')
    args = parser.parse_args()

    info("input.json = %s" % args.input_json)
    info("output.h = %s" % args.output_h)
    info("target key = %s" % args.key)
    json2fbs(args.input_json, args.output_h, args.key)
    exit(0)


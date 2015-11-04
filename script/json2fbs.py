#! /usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import codecs
import json
import re
import datetime
import argparse
import logging
from logging import info, warning, error
from collections import OrderedDict

def attribute_str(attributes):
    fbs_reserved_attributes = ('id', 'deprecated', 'required', 'original_order', 'force_align', 'bit_flags', 'nested_flatbuffer', 'key')
    if attributes:
        attrs = []
        for k, v in attributes.iteritems():
            if not k in fbs_reserved_attributes:
                continue
            if v == True:
                attrs.append(k)
            else:
                attrs.append(k+':'+v)
        return ' ('+', '.join(attrs)+')' if attrs else ''
    else:
        return ''

def generate_fbs(rootName, nameSpace, jsonData):
    s = "// generated by json2fbs.py\n\n"

    # output namespace
    s += "namespace {0};\n".format(nameSpace)

    # output tables
    for table_name in jsonData:
        if table_name == "_meta":
            s += 'table ' + rootName[0:1].upper() + rootName[1:] + " {\n"
        else:
            s += 'table ' + table_name[0:1].upper() + table_name[1:] + " {\n"
        for item in jsonData[table_name]:
            type_str = '['+item["type"]+']' if item['is_vector'] else item["type"];
            s += "    " + item["name"] + ":" + type_str + attribute_str(item["attribute"]) + ";\n"
        s += "}\n\n"

    # output root_type
    s += 'root_type {0};'.format(rootName)+"\n"
    return s

# ---
# root function
#
def json2fbs(input_json, output_fbs, rootName, nameSpace):
    with open(input_json, 'r') as f:
        jsonData = json.loads(f.read(), object_pairs_hook=OrderedDict)
        if isinstance(jsonData, dict):
            s = generate_fbs(rootName, nameSpace, jsonData)
            with open(output_fbs, 'w') as f:
                f.write(s.encode('utf-8'))
        else:
            print 'unsupported format. params:[{0}][{1}][{2}]'.format(input_json, rootName, nameSpace)

# ---
# main function
#
if __name__ == '__main__':
    sys.stdout = codecs.lookup('utf_8')[-1](sys.stdout)
    logging.basicConfig(level = logging.INFO, format = '%(asctime)-15s %(levelname)s %(message)s')
    parser = argparse.ArgumentParser(description = 'generate flatbuffers schema file (fbs) from json')
    parser.add_argument('input_json',  metavar = 'input.json',     help = 'input schema json file')
    parser.add_argument('output_fbs',  metavar = 'output.fbs',     help = 'output fbs file')
    parser.add_argument('--root-name', default = 'MasterDataFBS',  help = 'root node of flat buffers')
    parser.add_argument('--namespace', default = 'kms.masterdata', help = 'name space')
    args = parser.parse_args()

    info("input.json = %s" % args.input_json)
    info("output.fbs = %s" % args.output_fbs)
    info("root name = %s" % args.root_name)
    info("namespace = %s" % args.namespace)
    json2fbs(args.input_json, args.output_fbs, args.root_name, args.namespace)
    exit(0)

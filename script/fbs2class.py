#! /usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function
import sys
import re
import argparse
import logging
import pprint

from logging import info, warning, error
from collections import OrderedDict

def fbs2class(fbs, dst):
    with open(fbs, 'r') as f:
        global state, fbs_data
        state = "default"
        fbs_data = OrderedDict({})
        for line in f:
            if state == "default":
                parse_default(line)
            elif state == "table":
                parse_table(line)
    generate_classes(dst)

def parse_default(line):
    global state
    global fbs_data
    global fbs_root_type
    global fbs_namespace
    m = re.search('namespace\s+([^;]+);', line)
    if m != None:
        fbs_namespace = m.group(1)
        return
    m = re.search('root_type ([^;]+);', line)
    if m != None:
        fbs_root_type = m.group(1)
        return
    m = re.search('table\s+(\S+)\s+{', line)
    if m == None:
        return
    fbs_data[m.group(1)] = OrderedDict({})
    state = "table"

def parse_table(line):
    global state
    global fbs_data
    m = re.search('\s*\}', line)
    if m != None:
        state = "default"
        return
    m = re.search('\s*([^:]+):\[([^;]+)\];', line)
    if m != None:
        name = m.group(1)
        item = {'is_vector':True, 'item_type':m.group(2)}
    else:
        m = re.search('\s*([^:]+):([^;]+);', line)
        if m == None:
            return
        name = m.group(1)
        item = {'is_vector':False, 'item_type':m.group(2)}

    table_name = next(reversed(fbs_data))
    fbs_data[table_name][name] = item

def generate_classes(dst):
    global fbs_data
    global fbs_root_type
    global fbs_namespace

    s = "namespace " + fbs_namespace + " {\n"
    for table_name in fbs_data:
        table = fbs_data[table_name]
        s += "class " + table_name + " {\n protected:\n"
        for item_name in table:
            item = table[item_name]
            is_vector = item["is_vector"]
            item_type = item["item_type"]

            if is_vector:
                s += "  std::vector<" + item_type + "> _" + item_name + ";\n"
            else:
                s += "  " + item_type + " _" + item_name + ";\n"

        s += "\n public:\n"
        for item_name in table:
            item = table[item_name]
            is_vector = item["is_vector"]
            item_type = item["item_type"]
            is_default_type  = table_name in fbs_data

            if is_vector:
                s += "  std::vector<" + item_type + "> " + item_name + "() { return _" + item_name + ";}\n"
            elif is_default_type:
                s += "  " + item_type + " " + item_name + "() { return _" + item_name + "; }\n"
            else:
                s += "  " + item_type + " " + item_name + "() { return _" + item_name + "; }\n"
        s += "\n"
        for item_name in table:
            item = table[item_name]
            is_vector = item["is_vector"]
            item_type = item["item_type"]
            is_default_type  = table_name in fbs_data

            if is_default_type:
                s += "  void set" + item_name[0:1].upper() + item_name[1:]+ "(" + item_type + " value) { _" + item_name + " = value;}\n"

        s += "\n  // for FlatBuffers\n"
        s += "  " + table_name + "& operator=(const fbs::" + table_name + "& fb" + table_name + ") {\n"
        for item_name in table:
            item = table[item_name]
            is_vector = item["is_vector"]
            item_type = item["item_type"]
            fb_item_name = "fb" + table_name + "." + item_name + "()"
            if is_vector:
                s += "    _" + item_name + ".clear();\n"
                s += "    for (auto __" + item_name + " in " + fb_item_name + ") {\n"
                s += "      _" + item_name + ".push_back("+"__" + item_name + ");\n"
                s += "    }\n\n"
            else:
                s += "    _" + item_name + " = " + fb_item_name + ";\n"
        s += "    return *this;\n"
        s += "  }\n"

        s += "  flatbuffers::Offset<" + table_name + "> to_flatbuffers(flatbuffers::FlatBufferBuilder *fbb) {\n"
        for item_name in table:
            item = table[item_name]
            is_vector = item["is_vector"]
            item_type = item["item_type"]
            is_default_type  = table_name in fbs_data
            if is_vector:
                s += "    auto fb_" + item_name + " = flatbuffers::Vector<flatbuffers::Offset<" + item_type + ">();\n"
                s += "    for (auto __" + item_name + " in _" + item_name + ") {\n"
                s += "      fb_" + item_name + ".push_back(_" + item_name + ".to_flatbuffers(fbb));\n"
                s += "    }\n"
            elif is_default_type:
                s += "    auto fb_" + item_name + " = _" + item_name + ";\n"
            else:
                s += "    auto fb_" + item_name + " = _" + item_name + ".to_flatbuffers(fbb);\n"
        s += "    return Create(*fbb,\n"
        remains = len(table)
        for item_name in table:
            item = table[item_name]
            item_type = item["item_type"]
            s += "      fb_" + item_name
            remains -= 1
            if remains == 0:
                s += ");\n"
            else:
                s += ",\n"
        s += "  }\n"
        s += "}\n"
    s += "std::array<byte> serialize() {\n"
    s += "  FlatBufferBuilder fbb;\n"
    s += "  auto data = " + fbs_root_type + ".to_flatbuffers(&fbb);\n"
    s += "  fbb.Finish(data);\n"
    s += "  return std::array<byte>(fbb.GetBufferPointer(), fbb.GetSize());\n"
    s += "}\n"

    s += "array<byte> deserialize(const std::array<byte>& data) {\n"
    s += "  auto fb = Get" + fbs_root_type + "(data.data());\n"
    s += "  auto result = new " + fbs_root_type + "();\n"
    s += "  (*result) = fb;\n"
    s += "  return result;\n"
    s += "}\n"
    s += "} // namespace\n"

    with open(dst, 'w') as f:
        f.write(s)

# ---
# main function
#
if __name__ == '__main__':
    logging.basicConfig(level = logging.INFO, format = '%(asctime)-15s %(levelname)s %(message)s')

    parser = argparse.ArgumentParser(description = 'convert fbs schema to C++ classes')
    parser.add_argument('input_fbs',     metavar = 'input.fbs',  help = 'input FlatBuffers schema file')
    parser.add_argument('output_class',  metavar = 'output.h',   help = 'output class file (C++ header)')
    args = parser.parse_args()

    info("input  = %s" % args.input_fbs)
    info("output = %s" % args.output_class)
    fbs2class(args.input_fbs, args.output_class)
    exit(0)


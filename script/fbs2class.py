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

def fbs2class(fbs, dst, namespace):
    with open(fbs, 'r') as f:
        global state, fbs_data
        state = "default"
        fbs_data = OrderedDict({})
        for line in f:
            if state == "default":
                parse_default(line)
            elif state == "table":
                parse_table(line)
    generate_classes(dst, namespace)

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
    line = re.sub('\/\/.*', '', line)   # cut comment
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

def generate_classes(dst, namespace=None):
    global fbs_data
    global fbs_root_type
    global fbs_namespace

    s = ''
    s = '#include "user_data_generated.h"\n'
    namespace = namespace or fbs_namespace
    for ns in namespace.split('.'):
        s += "namespace " + ns + " {\n"

    s += "\n\n// class prototypes\n"
    for table_name in fbs_data:
        s += "class " + table_name + ";\n"

    s += "\n\n// main class definitions\n"
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

            if is_vector:
                s += "  std::vector<" + item_type + "> " + item_name + "() const { return _" + item_name + ";}\n"
            elif item_type == 'string':
                s += "  const " + item_type + "& " + item_name + "() const { return _" + item_name + "; }\n"
            else:
                s += "  " + item_type + " " + item_name + "() const { return _" + item_name + "; }\n"
        s += "\n"
        for item_name in table:
            item = table[item_name]
            is_vector = item["is_vector"]
            item_type = item["item_type"]
            is_default_type = table_name in fbs_data

            if is_vector:
                s += "  void set" + item_name[0:1].upper() + item_name[1:]+ "(std::vector<" + item_type + "> value) { _" + item_name + " = value;}\n"
            elif is_default_type:
                s += "  void set" + item_name[0:1].upper() + item_name[1:]+ "(" + item_type + " value) { _" + item_name + " = value;}\n"

        s += "\n  // for FlatBuffers\n"
        s += "#if 0  // FIXME have to support flatbuffers?\n"
        s += "  " + table_name + "& operator=(const " + table_name + "& fb" + table_name + ") {\n"
        for item_name in table:
            item = table[item_name]
            is_vector = item["is_vector"]
            item_type = item["item_type"]
            fb_item_name = "fb" + table_name + "." + item_name + "()"
            if is_vector:
                s += "    _" + item_name + ".clear();\n"
                s += "    for (auto& __" + item_name + " : " + fb_item_name + ") {\n"
                s += "      _" + item_name + ".push_back(__" + item_name + ");\n"
                s += "    }\n\n"
            else:
                s += "    _" + item_name + " = " + fb_item_name + ";\n"
        s += "    return *this;\n"
        s += "  }\n"

        # FIXME fbs::
        s += "  flatbuffers::Offset<fbs::" + table_name + "> to_flatbuffers(flatbuffers::FlatBufferBuilder *fbb) {\n"
        for item_name in table:
            item = table[item_name]
            is_vector = item["is_vector"]
            item_type = item["item_type"]
            is_default_type  = table_name in fbs_data
            if is_vector:
                s += "    // vector of " + item_name + "\n";
                s += "    std::vector<" + item_type + "> v_" + item_name + ";\n"
                s += "    for (auto& __" + item_name + " : _" + item_name + ") {\n"
                if item_type == 'string':
                    s += "      v_" + item_name + ".push_back(fbb->CreateString(__" + item_name + "));\n"
                elif is_default_type:
                    s += "      v_" + item_name + ".push_back(__" + item_name + ");\n"
                else:
                    s += "      v_" + item_name + ".push_back(__" + item_name + ".to_flatbuffers(fbb));\n"
                s += "    }\n"
                s += "    auto fb_" + item_name + " = fbb->CreateVector(v_" + item_name + ");\n"
            elif item_type == 'string':
                s += "    auto fb_" + item_name + " = fbb->CreateString(_" + item_name + ");\n"
            elif is_default_type:
                s += "    auto fb_" + item_name + " = _" + item_name + ";\n"
            else:
                s += "    auto fb_" + item_name + " = _" + item_name + ".to_flatbuffers(fbb);\n"
        s += "    return fbs::Create" + table_name[0:1].upper() + table_name[1:] + "(*fbb,\n"
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
        s += "#endif\n"
        s += "};\n" # end of class

    s += "\n";
    s += "#if 0\n"
    s += "std::vector<char> serialize() {\n"
    s += "  flatbuffers::FlatBufferBuilder fbb;\n"
    s += "  auto data = " + fbs_root_type + ".to_flatbuffers(&fbb);\n"
    s += "  fbb.Finish(data);\n"
    s += "  return std::vector<char>(fbb.GetBufferPointer(), fbb.GetSize());\n"
    s += "}\n\n"

    s += "vector<char> deserialize(const std::vector<char>& data) {\n"
    s += "  auto fb = Get" + fbs_root_type + "(data.data());\n"
    s += "  auto result = new " + fbs_root_type + "();\n"
    s += "  (*result) = fb;\n"
    s += "  return result;\n"
    s += "}\n\n"
    s += "#endif\n"

    for ns in namespace.split('.'):
        s += "} // namespace %s\n" % ns

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
    parser.add_argument('--namespace',   help = 'name space override')
    args = parser.parse_args()

    info("input  = %s" % args.input_fbs)
    info("output = %s" % args.output_class)
    info("namespace = %s" % args.namespace)
    fbs2class(args.input_fbs, args.output_class, args.namespace)
    exit(0)


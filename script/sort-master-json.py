#! /usr/bin/env python
# -*- coding: utf-8 -*-

import json
import sys
import re
from collections import OrderedDict
from pprint import pprint

def split_type(str):
    m = re.match("([^\(\)]+)\s*\((.*)\)", str)
    if m == None:
        n = str
        attrs = []
    else:
        n = m.group(1)
        attrs = m.group(2).split(" ")
    m = re.match("\s*\[([^\[\]+]+)\]\s*", n)
    if m == None:
        return (n, attrs, False)
    else:
        return (m.group(1), attrs, True)

def sort_master_json(schema, data, type_name = "_meta"):
    if not isinstance(data, dict):
        if isinstance(data, list):
            raise Exception("Error : %s" % type_name)
        return data
    result =  OrderedDict()
    currentSchema = schema[type_name]
    for key, entry in data.items():
        entry_type_str = [x for x in schema[type_name] if x["name"] == key][0]["type"]
        entry_type_name, entry_attributes, entry_is_array = split_type(entry_type_str)
        if type_name == "_meta":
            if entry_type_name == "json_array" or entry_type_name == "array":
                entry_is_array = True
            entry_type_name = key
        else:
            entry_type_name = entry_type_name[0].lower() + entry_type_name[1:]

        if entry_is_array:
            a = entry
            for entry_schema in schema[entry_type_name]:
                if entry_type_name == "areaInfo":
                    pprint(entry_schema)
                child_type_name, child_attributes, child_is_array = split_type(entry_schema["type"])
                child_type_name = child_type_name[0].lower() + child_type_name[1:]
                if child_type_name == "areaInfo":
                    print(child_type_name)
                    pprint(child_attributes)
                if "key" in child_attributes:
                    n = entry_schema["name"]
                    a = sorted(entry, cmp=lambda x, y:cmp(x[n], y[n])) 
                    break
            result[key] = []
            for i in a:
                result[key].append(sort_master_json(schema, i, entry_type_name))
        else:
            result[key] = sort_master_json(schema, entry, entry_type_name)
    return result

if __name__ == '__main__':
    schema_file = sys.argv[1]
    src_data_file = sys.argv[2]
    dst_data_file =  sys.argv[3]

    with open(schema_file, 'r') as f:
        schema = json.loads(f.read(), object_pairs_hook=OrderedDict)
    with open(src_data_file, 'r') as f:
        src_data = json.loads(f.read(), object_pairs_hook=OrderedDict)
    dst_data = sort_master_json(schema, src_data)
    with open(dst_data_file, 'w') as f:
        j = json.dumps(dst_data, ensure_ascii = False, indent = 4)
        f.write(j.encode("utf-8"))



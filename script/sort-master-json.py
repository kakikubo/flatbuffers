#! /usr/bin/env python
# -*- coding: utf-8 -*-

import json
import sys
import re
from collections import OrderedDict
from pprint import pprint

def sort_master_json(schema, data, type_name = "_meta"):
    if not isinstance(data, dict):
        if isinstance(data, list):
            raise Exception("Error : %s" % type_name)
        return data
    result =  OrderedDict()
    currentSchema = schema[type_name]
    for key, entry in data.items():
        entry_keys = [x for x in schema[type_name] if x["name"] == key]
        if not entry_keys:
            continue

        entry_is_array = False
        entry_type_str = entry_keys[0]["type"]
        m = re.match('\[(.*)\]', entry_type_str)
        if m:
            entry_is_array = True
            entry_type_str = m.group(1)

        if type_name == "_meta":
            if entry_type_str.find('array') >= 0:
                entry_is_array = True
            name = key
        else:
            name = entry_type_str[0].lower() + entry_type_str[1:]

        if entry_is_array:
            a = entry
            for entry_schema in schema[name]:
                if entry_schema["attribute"] and "key" in entry_schema["attribute"]:
                    n = entry_schema["name"]
                    a = sorted(entry, cmp=lambda x, y:cmp(x[n], y[n])) 
                    break
            result[key] = []
            for i in a:
                result[key].append(sort_master_json(schema, i, name))
        else:
            result[key] = sort_master_json(schema, entry, name)
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



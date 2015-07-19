#! /usr/bin/env python
# -*- coding: utf-8 -*-

import json
import sys
import re
from collections import OrderedDict

def sort_master_json(schema, data, type_name = "_meta"):
    if not isinstance(data, dict):
        if isinstance(data, list):
            raise Exception("data ist not list: %s" % type_name)
        return data
    result =  OrderedDict()
    currentSchema = schema[type_name]
    for key, entry in data.items():
        sch = [x for x in schema[type_name] if x["name"] == key]
        if not sch:
            continue
        sch = sch[0]
        type_str = sch["type"]
        name = type_str[0].lower() + type_str[1:]  # FIXME deprecated EnemyGroup -> enemyGroup

        if sch['is_vector']:
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



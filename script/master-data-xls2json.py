#!/usr/bin/env python
# -*- cording: utf-8 -*-
import sys
import re
import xlrd
import json
import codecs
import argparse
from collections import OrderedDict
from logging import error, warning

import ipdb
import pprint
pp = pprint.PrettyPrinter(indent = 4)

def parse_xls(xls_path, except_sheets=[]):
    data = OrderedDict()
    schema = OrderedDict()
    xls_book = xlrd.open_workbook(xls_path)
    for sheet in xls_book.sheets():
        if sheet.name in except_sheets:
            continue
        keys  = sheet.row(0)
        types = sheet.row(1)
        descs = sheet.row(2)
  
        sheet_schema = OrderedDict()
        for i, key in enumerate(keys):
            key = key.value
            sheet_schema[key] = {
                'name': key,
                'type': types[i].value,
                'description': descs[i].value
            }
        schema[sheet.name] = sheet_schema
  
        sheet_data = []
        for i in range(3, sheet.nrows):
            d = OrderedDict()
            row = sheet.row(i)
            try:
                for j, key in enumerate(keys):
                    v = row[j].value
                    k = key.value
                    t = types[j].value
                    if len(k) == 0:
                        continue;
                    elif t.find('ignore') >= 0:
                        continue
                    elif t.find('int') >= 0:
                        v = int(v) if v != '' else 0
                    elif t.find('float') >= 0:
                        v = float(v) if v != '' else 0
                    elif t.find('bool') >= 0:
                        v = bool(v)
                    else:
                        v = re.sub('\\n', "\n", "%s" % v)
                    d[k] = v 
            except:
                d['_error'] = "%s:%d:%d(%s) = %s: %s: %s" % (sheet.name, i, j, k, v, row, sys.exc_info())
                error(d['_error'])
            sheet_data.append(d)
        data[sheet.name] = sheet_data
    return {'data': data, 'schema': schema}
  
def normalize(data, schema, target):
    normalized = OrderedDict()
    for table in data['table']:
        if table['type'].find('ignore') >= 0:
            continue
        primary_key = table['primaryKey']
        version_key = table['versionKey']
  
        filtered = []
        id_mapping = OrderedDict()
        for d in data[table['name']]:
            if version_key in d:
                if d[version_key] != '' and d[version_key] != target:
                    continue
                del d[version_key]  # delete versionKey
  
            # filter by primary key
            if d[primary_key] is not None:
                if d[primary_key] >= 0:
                    id_mapping[d[primary_key]] = d  # override
                elif d[primary_key] < 0:
                    id = abs(d[primary_key])
                    if id in id_mapping:
                        del id_mapping[id]  # delete
            else:
              warning("no primary key record: %s: %s" % (table['name'], d))
  
        # object -> list
        filtered = []
        for id in id_mapping:
            filtered.append(id_mapping[id])
  
        if table['type'].find('object') >= 0:
            filtered = filtered[0] # by object, not object array
        normalized[table['name']] = filtered
    return normalized
  
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description = 'master data xlsx to json converter')
    parser.add_argument('input_xlsx',  metavar = 'input.xlsx',  help = 'input Excel master data file')
    parser.add_argument('schema_json', metavar = 'schema.json', help = 'output schema json file')
    parser.add_argument('data_json',   metavar = 'data.json',   help = 'output data json file')
    parser.add_argument('--target',        default = 'master',  help = 'target name (e.g. master, kiyoto.suzuki, ...) default: master')
    parser.add_argument('--except-sheets', default = 'enum',    help = 'except sheets (, separated list) default: enum')
    args = parser.parse_args()
  
    xls = parse_xls(args.input_xlsx, args.except_sheets.split(','))
    data = normalize(xls['data'], xls['schema'], args.target)
    for t in ((args.schema_json, xls['schema']), (args.data_json, data)):
        with codecs.open(t[0], "w") as fp:
            j = json.dumps(t[1], ensure_ascii = False, indent = 4)
            fp.write(j.encode("utf-8"))
    exit(0)

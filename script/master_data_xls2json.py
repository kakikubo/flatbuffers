#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8 ff=unix ft=python ts=4 sw=4 sts=4 si et fdm=indent fdl=99:
import sys
import os
import re
import xlrd
import json
import codecs
import argparse
import logging
from collections import OrderedDict
from logging import info, error, warning
from xlrd.biffh import (
    error_text_from_code,
    XL_CELL_BLANK,
    XL_CELL_TEXT,
    XL_CELL_BOOLEAN,
    XL_CELL_ERROR,
    XL_CELL_EMPTY,
    XL_CELL_DATE,
    XL_CELL_NUMBER
)
# error_text_from_code[value] 

import ipdb
import pprint
pp = pprint.PrettyPrinter(indent = 4)

def parse_xls(xls_path, except_sheets=[]):
    data = OrderedDict()
    schema = OrderedDict()
    xls_book = xlrd.open_workbook(xls_path)
    for sheet in xls_book.sheets():
        if sheet.name in except_sheets or re.match('^_', sheet.name):
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
                    c = row[j].ctype
                    if len(k) == 0:
                        continue
                    elif re.match('^_', k):
                        continue
                    elif t.find('ignore') >= 0:
                        continue
                    elif c == XL_CELL_ERROR:
                        raise Exception("Cell Error found: ctype = %d" % c)
                    #elif c in (XL_CELL_BLANK, XL_CELL_EMPTY):
                    #    continue
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
  
def normalize_schema(schema, tables):
    normalized = OrderedDict()
    meta = OrderedDict()
    for table in tables:
        if table['type'].find('ignore') >= 0:
            continue

        table_name = table['name']
        if table['type'].find('json') >= 0:
            normalized[table_name] = "swaped later"
        else:
            filtered = []
            for c in schema[table_name]:
                if c['type'].find('ignore') >= 0 or \
                   c['name'] == table['versionKey'] or \
                   re.match('^_', c['name']):
                    continue
                filtered.append(d)

            normalized[name] = filtered
        meta[name] = table
    normalized["_meta"] = meta
    return normalized
  
def normalize_data(data, target):
    normalized = OrderedDict()
    for table in data['table']:
        if table['type'].find('ignore') >= 0:
            continue
        filtered = []
        if table['type'].find('json') < 0:
            primary_key = table['primaryKey']
            version_key = table['versionKey']
      
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
            for id in id_mapping:
                filtered.append(id_mapping[id])
      
            if table['type'].find('object') >= 0:
                filtered = filtered[0] # by object, not object array
        normalized[table['name']] = filtered
    return normalized
  
if __name__ == '__main__':
    logging.basicConfig(level = logging.INFO, format = '%(asctime)-15s %(levelname)s %(message)s')

    parser = argparse.ArgumentParser(description = 'master data xlsx to json converter')
    parser.add_argument('input_xlsxes',    metavar = 'input.xlsx(es)',  nargs = "*", help = 'input Excel master data files')
    parser.add_argument('--schema-json',   metavar = 'schema.json', help = 'output schema json file. default:  master_schema.json')
    parser.add_argument('--data-json',     metavar = 'data.json',   help = 'output data json file. default:  master_data.json')
    parser.add_argument('--target',        default = 'master',  help = 'target name (e.g. master, kiyoto.suzuki, ...) default: master')
    parser.add_argument('--except-sheets', default = '',        help = 'except sheets (, separated list) default: ')
    args = parser.parse_args()
    schema_json_file = args.schema_json or 'master_schema.json'
    data_json_file   = args.data_json   or 'master_data.json'
    except_sheets    = args.except_sheets.split(',')
    
    # parse excel
    data   = OrderedDict()
    schema = OrderedDict()
    for input_xlsx in args.input_xlsxes:
        bname = os.path.basename(input_xlsx)
        if re.match('^~\$', bname):
            continue
        info("input: %s" % bname)
        xls = parse_xls(input_xlsx, except_sheets)
        data.update(xls['data'])
        schema.update(xls['schema'])
    for t in data['table']:
        info("table: %s" % t['name'])

    # write json
    schema = normalize_schema(schema, data['table'])
    data = normalize_data(data, args.target)
    for t in ((schema_json_file, schema), (data_json_file, data)):
        info("output: %s" % t[0])
        with codecs.open(t[0], "w") as fp:
            j = json.dumps(t[1], ensure_ascii = False, indent = 4)
            fp.write(j.encode("utf-8"))
    exit(0)

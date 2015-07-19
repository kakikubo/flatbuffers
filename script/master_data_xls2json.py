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

def parse_type(type_str):
    schema = OrderedDict()
    m = re.match("([^\(\)]+)\s*\((.*)\)", type_str)
    if m == None:
        schema['type'] = type_str
        schema['attribute'] = None
    else:
        attribute_map = OrderedDict()
        for attr_str in re.split('[,\s]+', m.group(2)):
            attr = re.split('[:\s]+', attr_str)
            if len(attr) > 1:
                attribute_map[attr[0]] = ':'.join(attr[1:])
            else:
                attribute_map[attr[0]] = True
        schema['type'] = m.group(1)
        schema['attribute'] = attribute_map if attribute_map else None
    schema['is_vector'] = False
    return schema

def parse_xls(xls_path, except_sheets=[]):
    data = OrderedDict()
    schema = OrderedDict()
    xls_book = xlrd.open_workbook(xls_path)
    for sheet in xls_book.sheets():
        if sheet.name in except_sheets or re.match('^_', sheet.name):
            continue
        try:
            keys  = sheet.row(0)
            types = sheet.row(1)
            descs = sheet.row(2)
        except:
            raise Exception("Empty sheet: %s" % sheet.name)
        if not sheet.nrows > 3:
            raise Exception("Empty data: %s" % sheet.name)
  
        sheet_schema = OrderedDict()
        for i, key in enumerate(keys):
            key = key.value
            sch = OrderedDict()
            sch['name'] = key
            sch['description'] = descs[i].value
            sch['file']  = os.path.basename(xls_path)
            sch['sheet'] = sheet.name
            sheet_schema[key] = sch
            sheet_schema[key].update(parse_type(types[i].value))
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
                        v = re.sub('\\\\n', "\n", "%s" % v)
                    d[k] = v 
            except:
                d['_error'] = "%s:%d:%d(%s) = %s: %s: %s" % (sheet.name, i, j, k, v, row, sys.exc_info())
                error(d['_error'])
                pass
            sheet_data.append(d)
        data[sheet.name] = sheet_data
    return {'data': data, 'schema': schema}

def check_data(data):
    errors = []
    for sheet in data['sheet']:
        if sheet['type'].find('ignore') >= 0:
            continue
        if sheet['type'].find('json') < 0:
            if not data.has_key(sheet['name']):
                errors.append("no data in sheet %s: %s" % (sheet['name'], ", ".join(data.keys())))
                continue
            for d in data[sheet['name']]:
                if d.has_key('_error'):
                    errors.append(d['_error'])
    if errors:
        print("\n---------------------------")
        print("    MASTER DATA ERROR      ")
        print("---------------------------")
        for e in errors:
            print(e)
        print("----------------------------\n")
        raise Exception("master data check error")
  
def normalize_schema(schema, sheets):
    normalized = OrderedDict()
    meta = []
    for sheet in sheets:
        if sheet['type'].find('ignore') >= 0:
            continue

        sheet_name = sheet['name']
        sheet['is_vector'] = sheet['type'].find('array') >= 0
        sheet['attribute'] = None
        if sheet['type'].find('json') >= 0:
            normalized[sheet_name] = "swapped later"
        else:
            filtered = []
            for name, d in schema[sheet_name].iteritems():
                if d['type'].find('ignore') >= 0 or \
                   re.match('^_', d['name']):
                    continue
                filtered.append(d)
            normalized[sheet_name] = filtered
        meta.append(sheet)
    normalized["_meta"] = meta
    return normalized
  
def normalize_data(data):
    normalized = OrderedDict()
    for sheet in data['sheet']:
        if sheet['type'].find('ignore') >= 0:
            continue
        filtered = []
        if sheet['type'].find('json') < 0:
            id_mapping = OrderedDict()
            for d in data[sheet['name']]:
                # filter by primary key
                if d['id'] is not None:
                    if d['id'] == 0:
                        # id = 0 is skipped
                        continue
                    elif d['id'] >= 0:
                        if id_mapping.has_key(d['id']):
                            raise Exception("Duplicated id %s in '%s'" % (d['id'], sheet['name']))
                        id_mapping[d['id']] = d  # override
                    elif d['id'] < 0:
                        id = abs(d['id'])
                        if id in id_mapping:
                            del id_mapping[id]  # delete
                else:
                  warning("no primary key record: %s: %s" % (sheet['name'], d))
      
            # object -> list
            for id in id_mapping:
                filtered.append(id_mapping[id])
      
            if sheet['type'].find('array') < 0:
                filtered = filtered[0] # by object, not object array
        normalized[sheet['name']] = filtered
    return normalized
  
if __name__ == '__main__':
    logging.basicConfig(level = logging.INFO, format = '%(asctime)-15s %(levelname)s %(message)s')

    parser = argparse.ArgumentParser(description = 'master data xlsx to json converter')
    parser.add_argument('input_xlsxes',    metavar = 'input.xlsx(es)',  nargs = "+", help = 'input Excel master data files')
    parser.add_argument('--schema-json',   metavar = 'schema.json', help = 'output schema json file. default:  master_schema.json')
    parser.add_argument('--data-json',     metavar = 'data.json',   help = 'output data json file. default:  master_data.json')
    parser.add_argument('--except-sheets', default = '',            help = 'except sheets (, separated list) default: ')
    parser.add_argument('--except-json',   default = False, action = 'store_true', help = 'except json master data (type = json, json_array)')
    args = parser.parse_args()
    schema_json_file = args.schema_json or 'master_schema.json'
    data_json_file   = args.data_json   or 'master_data.json'
    except_sheets    = args.except_sheets.split(',')
    except_json      = args.except_json
    
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

    data['sheet'] = sorted(data['sheet'], key=lambda v: int(v['id']))
    if args.except_json:
        sheet = []
        for t in data['sheet']:
            if not re.match('json', t['type']):
                sheet.append(t)
        data['sheet'] = sheet
    for t in data['sheet']:
        info("sheet: %s" % t['name'])

    # check error cells
    check_data(data)

    # write json
    schema = normalize_schema(schema, data['sheet'])
    data = normalize_data(data)
    for t in ((schema_json_file, schema), (data_json_file, data)):
        info("output: %s" % t[0])
        with codecs.open(t[0], "w") as fp:
            j = json.dumps(t[1], ensure_ascii = False, indent = 4)
            fp.write(j.encode("utf-8"))
    exit(0)

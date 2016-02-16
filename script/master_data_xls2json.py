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

def typed_numeric_value(cell, t):
    if t not in('byte', 'short', 'int', 'long', 'float'):
        raise Exception("invalid type: %s" % t)
    if cell.ctype != XL_CELL_NUMBER:
        raise Exception("got a non-numeric ctype: %s" % cell.ctype)

    if t in('byte', 'short', 'int'):
        return int(cell.value)
    elif t == 'long':
        return long(cell.value)
    if t == 'float':
        return float(cell.value)
    else:
        return None

def parse_enum_sheet(sheet):
    if sheet.ncols < 4 or sheet.ncols % 4 != 0:
        raise Exception("invalid column set: %s" % sheet.name)

    enums = OrderedDict()
    enum_desc = None
    enum_type = None
    enum_name = None

    for col_num in range(sheet.ncols):
        # parse definition columns
        if col_num % 4 == 0:
            if sheet.cell(0, col_num).ctype == XL_CELL_EMPTY:
                raise Exception("Enum Desc is not found: %s.column[%d]" % (sheet.name, col_num))
            if sheet.cell(1, col_num).ctype == XL_CELL_EMPTY:
                raise Exception("Enum Type is not found: %s.column[%d]" % (sheet.name, col_num))
            if sheet.cell(2, col_num).ctype == XL_CELL_EMPTY:
                raise Exception("Enum Name is not found: %s.column[%d]" % (sheet.name, col_num))

            enum_desc = sheet.cell(0, col_num).value
            enum_name = sheet.cell(1, col_num).value
            enum_type = sheet.cell(2, col_num).value

            enum_name = enum_name[0:1].upper() + enum_name[1:]
            if enum_name in enums:
                raise Exception("Duplicated enum name: %s" % enum_name)

            enums[enum_name] = OrderedDict()
            enums[enum_name]["is_enum"] = True
            enums[enum_name]["is_vector"] = False
            enums[enum_name]["description"] = enum_desc
            enums[enum_name]["type"] = enum_type
            enums[enum_name]["file"] = "enemy.xlsx"
            enums[enum_name]["sheet"] = "enemyEnum"
            enums[enum_name]["values"] = OrderedDict()

        # parse data columns
        else:
            for row_num in range(sheet.nrows):

                if sheet.cell(row_num, col_num).ctype == XL_CELL_EMPTY:
                    continue
                if row_num not in enums[enum_name]["values"]:
                    enums[enum_name]["values"][row_num] = OrderedDict()

                if col_num % 4 == 1:
                    enums[enum_name]["values"][row_num]['key'] \
                        = sheet.cell(row_num, col_num).value
                elif col_num % 4 == 2:
                    enums[enum_name]["values"][row_num]['description'] \
                        = sheet.cell(row_num, col_num).value
                elif col_num % 4 == 3:
                    enums[enum_name]["values"][row_num]['value'] \
                        = typed_numeric_value(sheet.cell(row_num, col_num), enum_type)
                else:
                    continue

    # verify entries
    for key, values in enums[enum_name]["values"].iteritems():
        if len(values) != 3:
            raise Exception("invalid item")

    return enums

def parse_xls(xls_path, except_sheets=[]):
    data = OrderedDict()
    schema = OrderedDict()
    xls_book = xlrd.open_workbook(xls_path)
    for sheet in xls_book.sheets():
        if re.match('[a-z][A-Za-z]+Enum$', sheet.name):
            enum_data = parse_enum_sheet(sheet)
            schema[sheet.name] = enum_data
            continue

        if sheet.name in except_sheets or re.match('^_', sheet.name):
            continue
        try:
            keys  = sheet.row(0)
            types = sheet.row(1)
            descs = sheet.row(2)
        except:
            error(u"空のシートがあります: %s" % sheet.name)
            raise Exception("empty sheet exists")
        if not sheet.nrows > 3:
            error(u"このシートのデータが空です: %s" % sheet.name)
            raise Exception("empty data in sheet")
  
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
                    elif re.match('^_', k) or t.find('ignore') >= 0:
                        v = v # keep ignored values in data json
                    elif c == XL_CELL_ERROR:
                        error(u"不正なセルの型です: key = %s ctype = %d" % (k, c))
                        raise Exception("invalid cell type")
                    #elif c in (XL_CELL_BLANK, XL_CELL_EMPTY):
                    #    continue
                    elif t.find('int') >= 0 or t.find('long') >= 0 or t.find('short') >= 0 or t.find('byte') >= 0:
                        v = int(v) if v != '' else 0
                    elif t.find('float') >= 0:
                        v = float(v) if v != '' else 0
                    elif t.find('bool') >= 0:
                        v = bool(v)
                    elif t.find('string') >= 0:
                        v = re.sub('\\\\n', "\n", "%s" % v)
                    else:
                        error(u"不正な型指定です: key = %s type = %s" % (k, t))
                        raise Exception("unknown cell type")
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
        if sheet['srcType'].find('ignore') >= 0:
            continue
        if sheet['srcType'].find('enum') >= 0:
            continue
        if sheet['srcType'].find('json') < 0:
            if not data.has_key(sheet['name']):
                errors.append(u"シート定義 '%s' の実体が存在しません: %s" % (sheet['name'], ", ".join(data.keys())))
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
        error(u"マスタデータチェックエラーです")
        raise Exception("Master Data Check Error")
  
def normalize_schema(schema, sheets):
    normalized = OrderedDict()
    meta = []
    for sheet in sheets:
        if sheet['srcType'].find('ignore') >= 0:
            continue

        sheet_name = sheet['name']
        sheet['is_vector'] = sheet['srcType'].find('array') >= 0
        sheet['attribute'] = None
        sheet['type'] = sheet_name[0].upper() + sheet_name[1:]
        if sheet['srcType'].find('json') >= 0:
            normalized[sheet['type']] = "swapped later"
        elif sheet['srcType'].find('enum') >= 0:
            for k, v in schema[sheet_name].iteritems():
                normalized[k] = v
        else:
            filtered = []
            for name, d in schema[sheet_name].iteritems():
                if d['type'].find('ignore') >= 0 or \
                   re.match('^_', d['name']):
                    continue
                filtered.append(d)
            normalized[sheet['type']] = filtered
        meta.append(sheet)
    normalized["_meta"] = meta
    return normalized
  
def normalize_data(data):
    normalized = OrderedDict()
    for sheet in data['sheet']:
        if sheet['srcType'].find('ignore') >= 0:
            continue
        if sheet['srcType'].find('enum') >= 0:
            continue
        filtered = []
        if sheet['srcType'].find('json') < 0:
            id_mapping = OrderedDict()
            for d in data[sheet['name']]:
                # filter by primary key
                if d['id'] is not None:
                    if d['id'] == 0:
                        # id = 0 is skipped
                        continue
                    elif d['id'] >= 0:
                        if id_mapping.has_key(d['id']):
                            error(u"テーブル %s で ID '%s' が重複しています" % (sheet['name'], d['id']))
                            raise Exception("duplicated id exists")
                        id_mapping[d['id']] = d  # override
                    elif d['id'] < 0:
                        id = abs(d['id'])
                        if id in id_mapping:
                            del id_mapping[id]  # delete
                else:
                    error(u"テーブル %s に主キーが空のレコードがあります: %s" % (sheet['name'], d))
                    raise Exception("some records has no primary key")
      
            # object -> list
            for id in id_mapping:
                filtered.append(id_mapping[id])
      
            if sheet['srcType'].find('array') < 0:
                filtered = filtered[0] # by object, not object array
        normalized[sheet['name']] = filtered
    return normalized
  
if __name__ == '__main__':
    sys.stdout = codecs.lookup('utf_8')[-1](sys.stdout)
    #sys.stderr = codecs.lookup('utf_8')[-1](sys.stderr)
    logging.basicConfig(level = logging.INFO, format = '%(asctime)-15s %(levelname)s %(message)s')

    parser = argparse.ArgumentParser(description = 'master data xlsx to json converter')
    parser.add_argument('input_xlsxes',    metavar = 'input.xlsx(es)',  nargs = "+", help = 'input Excel master data files')
    parser.add_argument('--schema-json',   metavar = 'schema.json', help = 'output schema json file. default:  master_schema.json')
    parser.add_argument('--data-json',     metavar = 'data.json',   help = 'output data json file. default:  master_data.json')
    parser.add_argument('--except-sheets', default = '',            help = 'except sheets (, separated list) default: ')
    parser.add_argument('--except-json',   default = False, action = 'store_true', help = 'except json master data (srcType = json, json_array)')
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
            if not re.match('json', t['srcType']):
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

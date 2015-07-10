#! /usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function
import os
import sys
import re
import argparse
import json
import logging
from logging import info, warning, error
from collections import OrderedDict
from glob import glob

def verify_record(table, i, d, id_map, meta, schema, reference, file_reference):
    pkey = meta['primaryKey']
    for k, v in d.iteritems():
        sch  = schema[k]
        ref  = reference[k] if reference and reference.has_key(k) else None
        fref = file_reference[k] if file_reference and file_reference.has_key(k) else None

        # check reference
        if ref:
            if not id_map.has_key(ref[0]):
                raise Exception("no reference target table: %s.%s -> %s" % (table, k, ref[0]))
            ref_data = id_map[ref[0]]
            if not ref_data.has_key(v):
                raise Exception("no reference data: %s[%d](%s).%s -> %s(%s)" % (table, i, d[pkey], k, ref[0], v))
        # check file reference
        if fref:
            path = ("kms_master_asset/"+fref).replace('{}', v)
            if not os.path.exists(path):
                raise Exception("referenced file does not exists: %s[%d](%s).%s -> %s in %s" % (table, i, d[pkey], k, v, fref))
    return True

def verify_master_json(src_schema, src_data):
    with open(src_schema, 'r') as f:
        master_schema = json.load(f, object_pairs_hook=OrderedDict)
    with open(src_data, 'r') as f:
        master_data = json.load(f, object_pairs_hook=OrderedDict)

    # create schema and reference map
    meta_map = OrderedDict()
    schema_map = OrderedDict()
    reference_map = OrderedDict()
    file_reference_map = OrderedDict()
    for table, schema in master_schema.iteritems():
        if table == '_meta':
            # create meta_map
            for sch in schema:
                meta_map[sch['name']] = sch
        else:
            schema_map[table] = OrderedDict()
            reference_map[table] = OrderedDict()
            file_reference_map[table] = OrderedDict()
            for sch in schema:
                name = sch['name']
                schema_map[table][name] = sch
                if sch['attribute']:
                    for k in sch['attribute']:
                        # file reference
                        file_ref = k.split('/')
                        if len(file_ref) > 1:
                            file_reference_map[table][name] = k
                            continue

                        # id reference
                        ref = k.split('.')
                        if len(ref) > 1:
                            if len(ref) > 2:
                                raise Exception("invalid reference: "+k)
                            reference_map[table][name] = ref


    # create id map
    id_map = OrderedDict()
    for table, data in master_data.iteritems():
        meta = meta_map[table]
        if meta['type'].find('array') >= 0:
            pkey = meta['primaryKey']
            id_map[table] = OrderedDict()
            for i, d in enumerate(data):
                if id_map[table].has_key(d[pkey]):
                    raise Exception("duplicated id: %s[%d](%s)", table, i, d[pkey])
                id_map[table][d[pkey]] = d

    # check master data main
    for table, data in master_data.iteritems():
        meta           = meta_map[table]
        schema         = schema_map[table]
        reference      = reference_map[table]
        file_reference = file_reference_map[table]
        try:
            if meta['type'].find('array') < 0:
                verify_record(table, 0, data, id_map, meta, schema, reference, file_reference)
            else:
                for i, d in enumerate(data):
                    verify_record(table, i, d, id_map, meta, schema, reference, file_reference)
        except Exception, e:
            print('=======================')
            print('  MASTER DATA ERROR    ')
            print('=======================')
            print(e)
            print('=======================')
            raise e

    return True

# ---
# main function
#
if __name__ == '__main__':
    logging.basicConfig(level = logging.INFO, format = '%(asctime)-15s %(levelname)s %(message)s')

    parser = argparse.ArgumentParser(description = 'verify master data json')
    parser.add_argument('input_schema', metavar = 'input.schema', help = 'input master data schema json file')
    parser.add_argument('input_data',   metavar = 'input.data',   help = 'input master data json file')
    args = parser.parse_args()

    info("input schema = %s" % args.input_schema)
    info("input data = %s" % args.input_data)
    verify_master_json(args.input_schema, args.input_data)
    info("no error is detected")
    exit(0)

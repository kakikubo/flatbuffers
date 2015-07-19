#! /usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function
import os
import sys
import re
import argparse
import json
import logging
from traceback import print_exception
from logging import info, warning, error
from collections import OrderedDict
from glob import glob

class MasterDataVerifier():
    def __init__(self, asset_dirs=None):
        self.master_schema      = None
        self.master_data        = None
        self.user_schema        = None
        self.user_data          = OrderedDict()
        self.asset_dirs         = asset_dirs

        self.meta_map           = None
        self.schema_map         = None
        self.reference_map      = None
        self.file_reference_map = None
        self.id_map             = None

        self.user_meta_map           = None
        self.user_schema_map         = None
        self.user_reference_map      = None
        self.user_file_reference_map = None
        self.user_id_map             = None

    def setup_data(self, schemas, data, meta_table_name):
        meta_map           = OrderedDict()
        schema_map         = OrderedDict()
        reference_map      = OrderedDict()
        file_reference_map = OrderedDict()
        for table, schema in schemas.iteritems():
            if table == meta_table_name:
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
                                #if len(ref) > 2:
                                #    raise Exception("invalid reference: "+k)
                                reference_map[table][name] = ref

        # create id map
        id_map = OrderedDict()
        for table, datum in data.iteritems():
            if re.match('^_', table):
                continue
            hkey = range_key = None
            if meta_map.has_key(table):
                meta = meta_map[table]
                if meta['type'].find('array') >= 0:
                    hkey = meta['hashKey'] # FIXME deprecated
                elif meta.has_key('is_vector') and meta['is_vector']:
                    table_type = meta['type']
                    if schema_map.has_key(table_type):
                        schema = schema_map[table_type]
                        for key, sch in schema.iteritems():
                            if sch['attribute'] and sch['attribute'].has_key('key'): # key = rangeKey
                                hkey = sch['name']
            if not hkey:
                continue

            id_map[table] = OrderedDict()
            for i, d in enumerate(datum):
                if d[hkey] <= 0:
                    continue
                if id_map[table].has_key(d[hkey]):
                    raise Exception("duplicated id: %s[%d](%s)", table, i, d[hkey])
                id_map[table][d[hkey]] = d

        return (meta_map, schema_map, reference_map, file_reference_map, id_map)

    def load_master_data(self, src_schema_file, src_data_file):
        with open(src_schema_file, 'r') as f:
            self.master_schema = json.load(f, object_pairs_hook=OrderedDict)
        with open(src_data_file, 'r') as f:
            self.master_data = json.load(f, object_pairs_hook=OrderedDict)

        # create schema and reference map
        self.meta_map, self.schema_map, self.reference_map, self.file_reference_map, self.id_map = \
                self.setup_data(self.master_schema, self.master_data, '_meta')
        return True

    def verify_master_record(self, table, i, d, schema, reference, file_reference):
        for k, v in d.iteritems():
            sch  = schema[k]
            ref  = reference[k] if reference and reference.has_key(k) else None
            fref = file_reference[k] if file_reference and file_reference.has_key(k) else None

            # check reference
            if ref and int(v) > 0:
                if not self.id_map.has_key(ref[0]):
                    raise Exception("no reference target table: %s.%s -> %s" % (table, k, ref[0]))
                ref_data = self.id_map[ref[0]]
                if not ref_data.has_key(v):
                    raise Exception("no reference data: %s[%d](%s).%s -> %s(%s)" % (table, i, d[hkey], k, ref[0], v))
            # check file reference
            if fref and self.asset_dirs:
                found = False
                for dir in self.asset_dirs:
                    path = (dir+"/"+fref).replace('{}', v)
                    if os.path.exists(path):
                        found = True
                if not found:
                    raise Exception("referenced file does not exists: %s[%d](%s).%s -> %s" % (table, i, d[hkey], k, v))
        return True

    def verify_master_data(self):
        # check master data main
        for table, data in self.master_data.iteritems():
            meta           = self.meta_map[table]
            schema         = self.schema_map[table]
            reference      = self.reference_map[table]
            file_reference = self.file_reference_map[table]
            try:
                if meta['type'].find('array') < 0:
                    self.verify_master_record(table, 0, data, schema, reference, file_reference)
                else:
                    for i, d in enumerate(data):
                        self.verify_master_record(table, i, d, schema, reference, file_reference)
            except:
                print('=======================')
                print('   MASTER DATA ERROR   ')
                print('=======================')
                t, v, b = sys.exc_info()
                print_exception(t, v, b)
                print('=======================')
                raise
        return True

    def load_user_data(self, user_schema_file, user_dirs):
        with open(user_schema_file, 'r') as f:
            self.user_schema = json.load(f, object_pairs_hook=OrderedDict)

        json_files = OrderedDict()
        for user_dir in user_dirs:
            for json_path in glob("%s/*.json" % user_dir):
                bname = os.path.basename(json_path)
                if re.match('^_', bname):
                    continue
                if json_files.has_key(bname):
                    continue
                json_files[bname] = json_path

        for bname, json_path in json_files.iteritems():
            key = re.sub('.json$', '', bname)
            info("load user data: %s" % bname)
            with open(json_path, 'r') as f:
                try:
                    self.user_data[key] = json.load(f, object_pairs_hook=OrderedDict)
                except ValueError, e:
                    print('=======================')
                    print('    USER DATA ERROR    ')
                    print('=======================')
                    print(json_path)
                    print(e)
                    print(check_output(["jq", ".", json_path]))
                    print('=======================')
                    raise e

        # create schema and reference map
        self.user_meta_map, self.user_schema_map, self.user_reference_map, self.user_file_reference_map, self.user_id_map = \
                self.setup_data(self.user_schema, self.user_data, 'UserDataFBS')
        return True

    def verify_user_record(self, table, i, d, schema, reference, file_reference):
        for k, v in d.iteritems():
            if re.match('^_', k):
                continue
            if not schema.has_key(k):
                raise Exception("invalid key exists: %s.%s (%s): '%s'" % (table, k, v, "', '".join(schema.keys())))
            sch  = schema[k]
            ref  = reference[k] if reference and reference.has_key(k) else None
            fref = file_reference[k] if file_reference and file_reference.has_key(k) else None

            if isinstance(v, OrderedDict) or isinstance(v, list):
                continue    # FIXME recursive

            # check master datareference
            if ref and int(v) > 0:
                if ref[0] == 'UserDataFBS':
                    if not self.user_id_map.has_key(ref[1]):
                        raise Exception("no reference target table: %s.%s -> %s.%s" % (table, k, ref[0], ref[1]))
                    ref_data = self.user_id_map[ref[1]]
                    if not ref_data.has_key(v):
                        raise Exception("no reference data: %s[%d](%s).%s -> %s.%s(%s)" % (table, i, d[hkey], k, ref[0], ref[1], v))
                else:
                    if not self.id_map.has_key(ref[0]):
                        raise Exception("no reference target table: %s.%s -> %s" % (table, k, ref[0]))
                    ref_data = self.id_map[ref[0]]
                    if not ref_data.has_key(v):
                        raise Exception("no reference data: %s[%d](%s).%s -> %s(%s)" % (table, i, d[hkey], k, ref[0], v))
            # check file reference
            if fref and self.asset_dirs:
                found = False
                for dir in self.asset_dirs:
                    path = (dir+"/"+fref).replace('{}', v)
                    if os.path.exists(path):
                        found = True
                if not found:
                    raise Exception("referenced file does not exists: %s[%d](%s).%s -> %s" % (table, i, d[hkey], k, v))
        return True

    def verify_user_data(self, user_data=None):
        # check user data main
        user_data = user_data or self.user_data
        for key, data in user_data.iteritems():
            meta = None
            if self.user_meta_map.has_key(key):
                meta = self.user_meta_map[key]
            else:
                for k, schema in self.user_schema_map.iteritems():
                    for l, s in schema.iteritems():
                        if key == s['name']:
                            meta = s
                            break
                    if meta:
                        break
                if not meta:
                    raise Exception('table is not defined: %s' % key)
            table = meta['type']
            info("verify user data: %s:%s" % (key, table))
            schema         = self.user_schema_map[table]
            reference      = self.user_reference_map[table]
            file_reference = self.user_file_reference_map[table]
            try:
                if meta['is_vector']:
                    for i, d in enumerate(data):
                        self.verify_user_record(table, i, d, schema, reference, file_reference)
                else:
                    self.verify_user_record(table, 0, data, schema, reference, file_reference)
            except:
                print('=======================')
                print('    USER DATA ERROR    ')
                print('=======================')
                print(key+' = '+json.dumps(data, indent=2).encode('utf-8'))
                t, v, b = sys.exc_info()
                print_exception(t, v, b)
                print('=======================')
                raise
        return True

# ---
# main function
#
if __name__ == '__main__':
    logging.basicConfig(level = logging.INFO, format = '%(asctime)-15s %(levelname)s %(message)s')

    parser = argparse.ArgumentParser(description = 'verify master data json')
    parser.add_argument('input_master_schema', metavar = 'input.master_schema', help = 'input master data schema json file')
    parser.add_argument('input_master_data',   metavar = 'input.master_data',   help = 'input master data json file')
    parser.add_argument('--user-schema', help = 'input user schema file')
    parser.add_argument('--user-dir', default = [], nargs='*', help = 'user data dir root default: .')
    parser.add_argument('--asset-dir', default = [], nargs='*', help = 'asset dir root default: .')
    args = parser.parse_args()

    info("input schema = %s" % args.input_master_schema)
    info("input data = %s" % args.input_master_data)
    info("user schema = %s", args.user_schema)
    info("user dir = %s", ', '.join(args.user_dir))
    info("asset dir = %s", ', '.join(args.asset_dir))
    verifier = MasterDataVerifier(args.asset_dir)
    verifier.load_master_data(args.input_master_schema, args.input_master_data)
    verifier.verify_master_data()
    if args.user_schema:
        verifier.load_user_data(args.user_schema, args.user_dir)
        verifier.verify_user_data()
    info("no error is detected")
    exit(0)

#! /usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function
import os
import sys
import re
import argparse
import json
import logging
from traceback import print_exc
from logging import info, warning, error
from collections import OrderedDict
from subprocess import check_call
from glob import glob

# TODO areaInfo.position.id 親の areaList の id とセットで語る必要がある
# TODO treasure.itemId -> material.id, petFood.id, keyItem.id, fish.id

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

    def upper_camel_case(self, src):
        return src[0:1].upper() + src[1:]

    def setup_data(self, schemas, data, meta_table_name):
        meta_map           = OrderedDict()
        schema_map         = OrderedDict()
        index_map          = OrderedDict()
        reference_map      = OrderedDict()
        file_reference_map = OrderedDict()
        for table, schema in schemas.iteritems():
            if table == meta_table_name:
                # create meta_map
                for sch in schema:
                    meta_map[sch['name']] = sch
                    meta_map[sch['type']] = sch
            else:
                # create reference map
                schema_map[table]         = OrderedDict()
                index_map[table]          = OrderedDict()
                reference_map[table]      = OrderedDict()
                file_reference_map[table] = OrderedDict()
                for sch in schema:
                    name = sch['name']
                    schema_map[table][name] = sch
                    if sch['attribute']:
                        for k, v in sch['attribute'].iteritems():
                            # id_map columns
                            if k in ('key', 'index'):
                                index_map[table][name] = sch

                            # file reference
                            file_ref = k.split('/')
                            if len(file_ref) > 1:
                                file_reference_map[table][name] = k
                                continue

                            # FIXME temporary skip  
                            if k in ('areaInfo.position.id'):
                                continue

                            # id reference
                            ref = k.split('.')
                            if len(ref) > 1:
                                if len(ref) > 3:
                                    raise Exception("invalid reference: "+k)
                                ref[0] = self.upper_camel_case(ref[0]) # treat reference as Table Type
                                if not reference_map[table].has_key(name):
                                    reference_map[table][name] = []
                                reference_map[table][name].append(ref)

        # create id map
        id_map = OrderedDict()
        for table, index_keys in index_map.iteritems():
            if not meta_map.has_key(table):
                continue
            meta = meta_map[table]
            datum = data[meta['name']] if data.has_key(meta['name']) else data[meta['type']]
            datum = datum if isinstance(datum, list) else [datum]
            for name, sch in index_keys.iteritems():
                id_map_key = table+'.'+name
                id_map[id_map_key] = OrderedDict()
                for i, d in enumerate(datum):
                    if not d.has_key(name):
                        raise KeyError("%s(%d) : %s" % (table, i, json.dumps(d)))
                    if d[name] <= 0:
                        continue
                    if id_map[id_map_key].has_key(d[name]) and sch['attribute'].has_key('key'):
                        raise Exception("duplicated id: %s[%d].%s(%s)" % (table, i, name, d[name]))
                    if not id_map[id_map_key].has_key(d[name]):
                        id_map[id_map_key][d[name]] = []
                    id_map[id_map_key][d[name]].append(d)

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

    def verify_reference(self, table, i, d, k, v, refs):
        if not refs or int(v) <= 0:
            return False

        src_id = None
        id_map_keys = []
        for ref in refs:
            if ref[0] == 'UserDataFBS':
                # user data reference
                id_map_key = 'User' + self.upper_camel_case(ref[1]) + '.' + ref[2]
                if not self.user_id_map.has_key(id_map_key):
                    raise Exception("no reference target table: %s.%s -> %s (%s.%s.%s)" % (table, k, id_map_key, ref[0], ref[1], ref[2]))
                id_map_keys.append(id_map_key)
                if d.has_key(ref[2]):
                    src_id = d[ref[2]]
            else:
                # master data reference
                id_map_key = ref[0]+'.'+ref[1]
                if not self.id_map.has_key(id_map_key):
                    raise Exception("no reference target table: %s.%s -> %s" % (table, k, id_map_key))
                id_map_keys.append(id_map_key)
                if d.has_key(ref[1]):
                    src_id = d[ref[1]]

        found = False
        for id_map_key in id_map_keys:
            ref_data = self.id_map[id_map_key] if self.id_map.has_key(id_map_key) else self.user_id_map[id_map_key]
            if ref_data.has_key(v):
                found = True
        if not found:
            raise Exception("no reference data: %s[%d](%s).%s -> %s(%s)" % (table, i, src_id, k, ' or '.join(id_map_keys), v))

        return True

    def verify_file_reference(self, table, i, d, k, v, fref):
        if fref and self.asset_dirs:
            found = False
            path = fref.replace('{}', str(v))
            for dir in self.asset_dirs:
                if os.path.exists(dir+'/'+path):
                    found = True
            if not found:
                raise Exception("referenced file does not exists: %s[%d].%s -> %s (%s)" % (table, i, k, v, path))
        return True

    def verify_master_record(self, table, i, d, schema, reference, file_reference):
        for k, v in d.iteritems():
            sch  = schema[k]
            refs = reference[k] if reference and reference.has_key(k) else []
            fref = file_reference[k] if file_reference and file_reference.has_key(k) else None
            self.verify_reference(table, i, d, k, v, refs)
            self.verify_file_reference(table, i, d, k, v, fref)
        return True

    def verify_master_data(self):
        # check master data main
        for table, data in self.master_data.iteritems():
            meta           = self.meta_map[table]
            table_type     = meta['type']
            schema         = self.schema_map[table_type]
            reference      = self.reference_map[table_type]
            file_reference = self.file_reference_map[table_type]
            try:
                if not meta['is_vector']:
                    self.verify_master_record(table, 0, data, schema, reference, file_reference)
                else:
                    for i, d in enumerate(data):
                        self.verify_master_record(table, i, d, schema, reference, file_reference)
            except:
                print('=======================')
                print('   MASTER DATA ERROR   ')
                print('=======================')
                print_exc()
                print('=======================')
                raise
        return True

    def load_user_data(self, user_schema_file, user_data_file):
        try:
            with open(user_schema_file, 'r') as f:
                self.user_schema = json.load(f, object_pairs_hook=OrderedDict)
            with open(user_data_file, 'r') as f:
                    self.user_data = json.load(f, object_pairs_hook=OrderedDict)
        except ValueError, e:
            print('=======================')
            print('    USER DATA ERROR    ')
            print('=======================')
            print(f.name)
            print(e)
            print(check_call(["jq", ".", f.name]))
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
            refs = reference[k] if reference and reference.has_key(k) else []
            fref = file_reference[k] if file_reference and file_reference.has_key(k) else None
            if isinstance(v, OrderedDict) or isinstance(v, list):
                continue    # FIXME recursive
            self.verify_reference(table, i, d, k, v, refs)
            self.verify_file_reference(table, i, d, k, v, fref)
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
                print_exc()
                print('=======================')
                raise
        return True


    def generate_location_reference_tree(self, location_reference_tree_file):
        # TODO
        #print(json.dumps(self.meta_map, indent=2))
        #print(json.dumps(self.schema_map, indent=2))
        #print(json.dumps(self.reference_map, indent=2))
        #print(json.dumps(self.file_reference_map, indent=2))
        print(json.dumps(self.id_map, indent=2))

# ---
# main function
#
if __name__ == '__main__':
    logging.basicConfig(level = logging.INFO, format = '%(asctime)-15s %(levelname)s %(message)s')

    parser = argparse.ArgumentParser(description = 'verify master data json')
    parser.add_argument('input_master_schema', metavar = 'input.master_schema', help = 'input master data schema json file')
    parser.add_argument('input_master_data',   metavar = 'input.master_data',   help = 'input master data json file')
    parser.add_argument('--user-schema', help = 'input user schema file')
    parser.add_argument('--user-data', help = 'input user data json file ')
    parser.add_argument('--asset-dir', default = [], nargs='*', help = 'asset dir root default: .')
    parser.add_argument('--location-reference-tree', help = 'generate reference tree by location')
    args = parser.parse_args()

    info("input master schema = %s" % args.input_master_schema)
    info("input master data = %s" % args.input_master_data)
    info("input user schema = %s", args.user_schema)
    info("input user data = %s", args.user_data)
    info("input asset dir = %s", ', '.join(args.asset_dir))
    info("output location reference tree = %s", args.location_reference_tree)
    verifier = MasterDataVerifier(args.asset_dir)
    verifier.load_master_data(args.input_master_schema, args.input_master_data)
    verifier.verify_master_data()
    if args.user_schema:
        verifier.load_user_data(args.user_schema, args.user_data)
        verifier.verify_user_data()
    #verifier.generate_location_reference_tree(args.location_reference_tree)
    info("no error is detected")
    exit(0)

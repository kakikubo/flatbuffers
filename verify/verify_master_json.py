#! /usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function
import os
import sys
import re
import codecs
import argparse
import importlib
import json
import logging
from traceback import print_exc
from logging import info, debug, warning, error
from collections import OrderedDict
from subprocess import check_call
from glob import glob

# TODO areaInfo.position.id 親の areaList の id とセットで語る必要がある
# TODO enemySpine.id -> contents/files/spine/enemySpine/{}.png, contents/files/spine/enemySpine/{}.atlas, contents/files/spine/enemySpine/{}.json
# x characterJob.id -> contents/files/thumb/job/{}.png

class MasterDataVerifier():
    def __init__(self, asset_dirs=None, verify_file_reference=True):
        self.master_schema      = None
        self.master_data        = None
        self.user_schema        = None
        self.user_data          = OrderedDict()
        self.asset_dirs         = asset_dirs

        self.meta_map           = None
        self.schema_map         = None
        self.index_map          = None
        self.reference_map      = None
        self.referenced_map     = None
        self.file_reference_map = None
        self.id_map             = None
        self.referenced_id_map  = None
        self.validation_map     = None

        self.user_meta_map           = None
        self.user_schema_map         = None
        self.user_index_map          = None
        self.user_reference_map      = None
        self.user_referenced_map     = None
        self.user_file_reference_map = None
        self.user_id_map             = None
        self.user_referenced_id_map  = None
        self.user_validation_map     = None

        self.do_verify_file_reference = verify_file_reference

    def load_table_verifier(self, module_name):
        m = importlib.import_module(module_name)
        c = getattr(m, module_name.split('.')[-1])
        return c()

    def upper_camel_case(self, src):
        return src[0:1].upper() + src[1:]

    def lower_camel_case(self, src):
        return src[0:1].lower() + src[1:]

    def setup_data(self, schemas, data, meta_table_name):
        meta_map           = OrderedDict()
        schema_map         = OrderedDict()
        index_map          = OrderedDict()
        reference_map      = OrderedDict()
        file_reference_map = OrderedDict()
        validation_map     = OrderedDict()
        for table, schema in schemas.iteritems():
            # skip enum schema
            if isinstance(schema, dict):
                continue

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
                validation_map[table]     = OrderedDict()
                for sch in schema:
                    name = sch['name']
                    schema_map[table][name] = sch
                    if sch.has_key('attribute') and sch['attribute']:
                        for k, v in sch['attribute'].iteritems():
                            if k in ('key', 'index'):
                                # id_map columns
                                index_map[table][name] = sch
                            elif k in ('max_length', 'max_value', 'min_length', 'min_value', 'required'):
                                # value spec
                                if not validation_map[table].has_key(name):
                                    validation_map[table][name] = {}
                                validation_map[table][name][k] = v
                            elif k == 'file_reference':
                                # file reference
                                for fref, required in v.iteritems():
                                    if not file_reference_map[table].has_key(name):
                                        file_reference_map[table][name] = {}
                                    file_reference_map[table][name][fref] = required
                            elif k == 'reference':
                                # id reference
                                for ref, required in v.iteritems():
                                    # FIXME temporary skip  
                                    if ref in ('areaInfo.position.id'):
                                        continue
                                    refs = ref.split('.')
                                    if len(refs) > 3:
                                        error(u"不正な参照定義です: "+v)
                                        raise Exception("invalid reference definition")
                                    refs[0] = self.upper_camel_case(refs[0]) # treat reference as Table Type
                                    if not reference_map[table].has_key(name):
                                        reference_map[table][name] = []
                                    reference_map[table][name].append(refs)

        # create id map
        id_map = OrderedDict()
        for table, index_keys in index_map.iteritems():
            if not meta_map.has_key(table):
                continue
            meta = meta_map[table]
            datum = data[meta['name']] if data.has_key(meta['name']) else data[meta['type']]
            datum = datum if isinstance(datum, list) else [datum]
            for name, sch in index_keys.iteritems():
                if not id_map.has_key(table):
                    id_map[table] = OrderedDict()
                id_map[table][name] = OrderedDict()
                for i, d in enumerate(datum):
                    if not d.has_key(name):
                        raise KeyError("%s(%d) : %s" % (table, i, json.dumps(d)))
                    if d[name] <= 0:
                        continue
                    if id_map[table][name].has_key(d[name]) and sch['attribute'].has_key('key'):
                        error(u"ID が重複しています: %s[%d].%s(%s)" % (table, i, name, d[name]))
                        raise Exception("duplicated id")
                    if not id_map[table][name].has_key(d[name]):
                        id_map[table][name][d[name]] = []
                    id_map[table][name][d[name]].append(d)

        return (meta_map, schema_map, index_map, reference_map, file_reference_map, id_map, validation_map)

    def load_master_data(self, src_schema_file, src_data_file):
        with open(src_schema_file, 'r') as f:
            self.master_schema = json.load(f, object_pairs_hook=OrderedDict)
        with open(src_data_file, 'r') as f:
            self.master_data = json.load(f, object_pairs_hook=OrderedDict)

        # create schema and reference map
        self.meta_map, self.schema_map, self.index_map, self.reference_map, self.file_reference_map, self.id_map, self.validation_map = \
                self.setup_data(self.master_schema, self.master_data, '_meta')
        return True

    def verify_reference(self, table, i, d, k, v, refs):
        if not refs or not v:
            return False
        if (isinstance(v, str) and v.isdigit() and int(v) <= 0) or v <= 0:
            return False

        src_id = None
        id_map_keys = []
        for ref in refs:
            if ref[0] == 'UserDataFBS':
                # user data reference
                ref_table = 'User' + self.upper_camel_case(ref[1])
                if not self.user_id_map.has_key(ref_table) or not self.user_id_map[ref_table].has_key(ref[2]):
                    error(u"参照先のテーブル指定が不正です: %s.%s -> %s.%s (%s.%s.%s)" % (table, k, ref_table, ref[2], ref[0], ref[1], ref[2]))
                    raise Exception("invalid table reference")
                id_map_keys.append([ref_table, ref[2]])
                if d.has_key(ref[2]):
                    src_id = d[ref[2]]
            else:
                # master data reference
                if not self.id_map.has_key(ref[0]) or not self.id_map[ref[0]].has_key(ref[1]):
                    error(u"参照先のテーブル指定が不正です: %s.%s -> %s.%s" % (table, k, ref[0], ref[1]))
                    raise Exception("invalid table reference")
                id_map_keys.append([ref[0], ref[1]])
                if d.has_key(ref[1]):
                    src_id = d[ref[1]]

        found = False
        for ref in id_map_keys:
            ref_data = self.id_map[ref[0]] if self.id_map.has_key(ref[0]) else self.user_id_map[ref[0]]
            if ref_data.has_key(ref[1]) and ref_data[ref[1]].has_key(v):
                found = True
        if not found:
            keys = [key[0]+'.'+key[1] for key in id_map_keys]
            error(u"参照先のデータがありません: %s[%d](%s).%s -> %s(%s)" % (table, i, src_id, k, ' or '.join(keys), v))
            raise Exception("no referenced data")

        return True

    def verify_file_reference(self, table, i, d, k, v, frefs):
        if frefs and self.asset_dirs:
            for fref, required in frefs.iteritems():
                if not required:
                    continue
                found = False
                path = self.complete_file_path(fref, v, d)
                for dir in self.asset_dirs:
                    if glob(os.path.join(dir, path)):
                        found = True
                if not found:
                    error(u"参照しているファイルがありません: %s[%d].%s -> %s (%s)" % (table, i, k, v, path))
                    raise Exception("no referenced file")
        return True

    def verify_master_record(self, table, i, d, schema, reference, file_reference, validation_spec):
        for k, v in d.iteritems():
            sch  = schema[k]
            refs = reference[k] if reference and reference.has_key(k) else []
            frefs = file_reference[k] if file_reference and file_reference.has_key(k) else None
            validations = validation_spec[k] if validation_spec and validation_spec.has_key(k) else []
            value_type = sch["type"]
            self.verify_reference(table, i, d, k, v, refs)
            if self.do_verify_file_reference:
                self.verify_file_reference(table, i, d, k, v, frefs)
            self.verify_value_spec(table, i, d, k, v, value_type, validations)
        return True

    def verify_value_spec(self, table, i, d, k, v, value_type, validations):
        if validations and self.validation_map:
            for item, spec in validations.iteritems():
                try:
                    has_err = self.has_err(v, item, value_type, spec)
                except:
                    error(u"%s[%d].%s: 不正な値があります (%s: %s): %s" %(table, i, k, item, spec, unicode(v)))
                    raise
                if has_err:
                    error(u"%s[%d].%s: 不正な値があります (%s: %s): %s" %(table, i, k, item, spec, unicode(v)))
                    raise Exception("invalid value spec")
        if k == 'label':
            if v and not re.match('^[a-z0-9_./]+$', v):
                error(u"%s[%d].%s: 不正なラベルです: %s" % (table, i, k, unicode(v)))
                raise Exception("invalid filename name")

    @staticmethod
    def has_err(v, i, value_type, value_spec):
        if value_type == 'string' and i == 'max_length':
            return len(v) > value_spec
        if value_type == 'string' and i == 'min_length':
            return len(v) < value_spec
        if value_type in('int', 'long') and i == 'max_value':
            return v > int(value_spec)
        if value_type in('float') and i == 'max_value':
            return v > float(value_spec)
        if value_type in('int', 'long') and i == 'min_value':
            return v < int(value_spec)
        if value_type in('float') and i == 'min_value':
            return v < float(value_spec)
        if value_type == 'string' and i == 'required':
            return  (v is None or len(v) == 0)

        return False

    def verify_master_data(self):
        # check master data main
        for table, data in self.master_data.iteritems():
            meta           = self.meta_map[table]
            table_type     = meta['type']
            schema         = self.schema_map[table_type]
            reference      = self.reference_map[table_type]
            file_reference = self.file_reference_map[table_type]
            validations    = self.validation_map[table_type] if self.validation_map.has_key(table_type) else []
            try:
                if not meta['is_vector']:
                    self.verify_master_record(table, 0, data, schema, reference, file_reference, validations)
                else:
                    for i, d in enumerate(data):
                        self.verify_master_record(table, i, d, schema, reference, file_reference, validations)

                if os.path.exists(os.path.join(os.path.dirname(__file__), 'master_data', table+'.py')):
                     table_verifier = self.load_table_verifier('master_data.'+table)
                     if not table_verifier.verify(data, schema, reference, file_reference, validations):
                         raise Exception("some taable validation errors are detected: %s" % table)
            except:
                print('=======================')
                print('   MASTER DATA ERROR   ')
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
        self.user_meta_map, self.user_schema_map, self.user_index_map, self.user_reference_map, self.user_file_reference_map, self.user_id_map, self.user_validation_map = \
                self.setup_data(self.user_schema, self.user_data, 'UserDataFBS')
        return True

    def verify_user_record(self, table, i, d, schema, reference, file_reference, validation_spec):
        for k, v in d.iteritems():
            if re.match('^_', k):
                continue
            if not schema.has_key(k):
                error(u"存在しないテーブルにデータを置いています: %s.%s (%s): '%s'" % (table, k, v, "', '".join(schema.keys())))
                raise Exception("put data onto unexisted table")
            sch  = schema[k]
            refs = reference[k] if reference and reference.has_key(k) else []
            fref = file_reference[k] if file_reference and file_reference.has_key(k) else None
            validations = validation_spec[k] if validation_spec and validation_spec.has_key(k) else []
            value_type = sch["type"]
            if isinstance(v, OrderedDict) or isinstance(v, list):
                continue    # FIXME recursive
            self.verify_reference(table, i, d, k, v, refs)
            if self.do_verify_file_reference:
                self.verify_file_reference(table, i, d, k, v, fref)
            self.verify_value_spec(table, i, d, k, v, value_type, validations)
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
                    error(u'テーブルがありません: %s' % key)
                    raise Exception('no table exists')
            table = meta['type']
            info("verify user data: %s:%s" % (key, table))
            schema         = self.user_schema_map[table]
            reference      = self.user_reference_map[table]
            file_reference = self.user_file_reference_map[table]
            validations    = self.validation_map[table] if self.validation_map.has_key(table) else []
            try:
                if meta['is_vector']:
                    for i, d in enumerate(data):
                        self.verify_user_record(table, i, d, schema, reference, file_reference, validations)
                else:
                    self.verify_user_record(table, 0, data, schema, reference, file_reference, validations)
            except:
                print('=======================')
                print('    USER DATA ERROR    ')
                print('=======================')
                print(key+' = '+json.dumps(data, indent=2).encode('utf-8'))
                print_exc()
                print('=======================')
                raise
        return True

    def create_referenced_map(self, reference_map):
        # create referenced map
        referenced_map = OrderedDict()
        for table, ref_map in reference_map.iteritems():
            for ref, refed_list in ref_map.iteritems():
                for refed in refed_list:
                    if refed[0] == 'UserDataFBS':
                        prefix      = ''
                        #ref_table   = 'User'+table
                        ref_table   = table
                        refed_table = 'User'+self.upper_camel_case(refed[1])
                        refed_name  = refed[2]
                        index_map   = self.user_index_map
                    else:
                        #prefix      = 'Master'
                        prefix      = ''
                        #ref_table   = 'Master'+table
                        ref_table   = table # TODO index_map or user_index_map
                        refed_table = self.upper_camel_case(refed[0])
                        refed_name  = refed[1]
                        index_map   = self.index_map
                    if index_map.has_key(refed_table) and index_map[refed_table].has_key(refed_name):
                        refed_table_key = prefix+refed_table
                        if not referenced_map.has_key(refed_table_key):
                            referenced_map[refed_table_key] = OrderedDict()
                        if not referenced_map[refed_table_key].has_key(refed_name):
                            referenced_map[refed_table_key][refed_name] = []
                        referenced_map[refed_table_key][refed_name].append({ref_table: ref})
                    elif refed_name == 'position':
                        continue    # TODO
                    else:
                        error(u"対象のテーブルがインデックス定義されていません: %s.%s -> %s.%s" % (ref_table, ref, refed_table, refed_name))
                        raise Exception("no index for target table")
                        continue
        return referenced_map

    def create_referenced_id_map(self, referenced_map, data, id_map):
        referenced_id_map = OrderedDict()
        for table, refed_map in referenced_map.iteritems():
            referenced_id_map[table] = OrderedDict()
            for refed, ref_list in refed_map.iteritems():
                for ref in ref_list:
                    for ref_table, ref_name in ref.iteritems():
                        if not isinstance(data[self.lower_camel_case(ref_table)], list):
                            continue
                        for d in data[self.lower_camel_case(ref_table)]:
                            ref_id = d[ref_name]
                            if not id_map[table][refed].has_key(ref_id):
                                continue
                            refed_data = id_map[table][refed][ref_id]
                            if not referenced_id_map[table].has_key(refed):
                                referenced_id_map[table][refed] = OrderedDict()
                            if not referenced_id_map[table][refed].has_key(ref_id):
                                referenced_id_map[table][refed][ref_id] = []
                            referenced_id_map[table][refed][ref_id].append({ref_table: {ref_name: d}})
        return referenced_id_map

    def complete_file_path(self, path, v, d):
        path = path.replace('{}', str(v))
        m = re.search('\{([^}]+)\}', path)
        if m:
            for k in m.groups():
                if not d.has_key(k):
                    error(u"不正なファイルパスがあります: %s: %s" % (k, path))
                    raise Exception("invalid path exists")
                path = path.replace('{'+k+'}', str(d[k]))
        return path

    # TODO support user data
    def collect_file_list(self, table, key, id, root_id, septums, is_septum, visited_map):
        if visited_map.has_key(table) and visited_map[table].has_key(key) and visited_map[table][key].has_key(id):
            return []
        if not self.id_map[table].has_key(key) or not self.id_map[table][key].has_key(id):
            return []
        if not visited_map.has_key(table):
            visited_map[table] = OrderedDict()
        if not visited_map[table].has_key(key):
            visited_map[table][key] = OrderedDict()
        visited_map[table][key][id] = True

        dest = []
        for d in self.id_map[table][key][id]:
            # add file reference
            if self.file_reference_map.has_key(table):
                for fref, paths in self.file_reference_map[table].iteritems():
                    for path, required in paths.iteritems():
                        debug('%d: file %s.%s(%s) -> %s(%s): %s' % (root_id, table, key, id, fref, d[fref], path))
                        for asset_dir in self.asset_dirs:
                            glob_path = os.path.join(asset_dir, self.complete_file_path(path, d[fref], d))
                            debug("%d: glob: %s" % (root_id, glob_path))
                            for file in glob(glob_path):
                                dest.append(re.sub('^'+asset_dir+'/', '', file))
            if is_septum:
                continue

            # recursive for referenced
            if self.referenced_id_map.has_key(table) and self.referenced_id_map[table].has_key(key) and self.referenced_id_map[table][key].has_key(id):
                for ref in self.referenced_id_map[table][key][id]:
                    for ref_table, ref_data in ref.iteritems():
                        is_septum = ref_table in septums
                        schema = self.schema_map[ref_table]
                        for name, sch in schema.iteritems():
                            if sch['attribute'] and sch['attribute'].has_key('key'):
                                for ref_name, data in ref_data.iteritems():
                                    debug('%d: from %s.%s(%s) -> %s.%s -> %s.%s(%s): %s' % (root_id, table, key, id, ref_table, ref_name, ref_table, name, data[name], is_septum))
                                    dest += self.collect_file_list(ref_table, name, data[name], root_id, septums, is_septum, visited_map)

            # recursive for reference
            if self.reference_map.has_key(table):
                for name, refs in self.reference_map[table].iteritems():
                    for ref in refs:
                        is_septum = ref[0] in septums
                        debug('%d: to %s(%s).%s -> %s.%s(%s): %s' % (root_id, table, id, name, ref[0], ref[1], d[name], is_septum))
                        dest += self.collect_file_list(ref[0], ref[1], d[name], root_id, septums, is_septum, visited_map)
        return dest

    def generate_file_reference_list(self, dest_dir):
        self.referenced_map      = self.create_referenced_map(self.reference_map)
        #self.user_referenced_map = self.create_referenced_map(self.user_reference_map)
        self.referenced_id_map   = self.create_referenced_id_map(self.referenced_map, self.master_data, self.id_map)
        septums = []
        for sheet in self.master_data['sheet']:
            if sheet['referenceSeptum']:
                septums.append(self.upper_camel_case(sheet['name']))
        info("reference septums: %s" % ', '.join(septums))

        # create referenced file list from Location
        location_file_list = OrderedDict()
        for d in self.master_data['location']:
            l = self.collect_file_list('Location', 'id', d['id'], d['id'], septums, False, OrderedDict())
            location_file_list[d['id']] = sorted(dict(zip(l[0::1], l[0::1])).keys())
        info("generate file reference list: location_file_list.json: %d" % len(location_file_list))
        with open(os.path.join(dest_dir, 'location_file_list.json'), 'w') as f:
            json.dump(location_file_list, f, indent=2)

        # create referenced file list from Character
        character_file_list = OrderedDict()
        for d in self.master_data['character']:
            l = self.collect_file_list('Character', 'id', d['id'], d['id'], septums, False, OrderedDict())
            character_file_list[d['id']] = sorted(dict(zip(l[0::1], l[0::1])).keys())
        info("generate file reference list: character_file_list.json: %d" % len(character_file_list))
        with open(os.path.join(dest_dir, 'character_file_list.json'), 'w') as f:
            json.dump(character_file_list, f, indent=2)

        # create referenced file list from LayoutLoader
        ui_file_list = OrderedDict()
        for d in self.master_data['layoutLoader']:
            l = self.collect_file_list('LayoutLoader', 'id', d['id'], d['id'], septums, False, OrderedDict())
            ui_file_list[d['id']] = sorted(dict(zip(l[0::1], l[0::1])).keys())
        info("generate file reference list: ui_file_list.json: %d" % len(ui_file_list))
        with open(os.path.join(dest_dir, 'ui_file_list.json'), 'w') as f:
            json.dump(ui_file_list, f, indent=2)

        return True

# ---
# main function
#
if __name__ == '__main__':
    sys.stdout = codecs.lookup('utf_8')[-1](sys.stdout)
    #sys.stderr = codecs.lookup('utf_8')[-1](sys.stderr)
    parser = argparse.ArgumentParser(description='verify master data and default user data, and generate file reference list', epilog="""\
example:
    $ ./verify_master_json.py master_derivatives/master_schema.json master_derivatives/master_data.json --file-reference-list manifests --asset-dir kms_master_asset kms_master_asset --user-schema user_derivatives/user_schema.json --user-data user_data/default.json --verify-file-reference""")
    parser.add_argument('input_master_schema', metavar = 'input.master_schema', help = 'input master data schema json file')
    parser.add_argument('input_master_data',   metavar = 'input.master_data',   help = 'input master data json file')
    parser.add_argument('--user-schema', help = 'input user schema file')
    parser.add_argument('--user-data', help = 'input user data json file ')
    parser.add_argument('--asset-dir', default = [], nargs='*', help = 'asset dir root default: .')
    parser.add_argument('--verify-file-reference', default = False, action = 'store_true', help = 'verify file reference')
    parser.add_argument('--file-reference-list', help = 'output dir of referenced file lists generated')
    parser.add_argument('--log-level', help = 'log level (WARNING|INFO|DEBUG). default: INFO')
    args = parser.parse_args()
    logging.basicConfig(level = args.log_level or "INFO", format = '%(asctime)-15s %(levelname)s %(message)s')

    info("input master schema = %s" % args.input_master_schema)
    info("input master data = %s" % args.input_master_data)
    info("input user schema = %s", args.user_schema)
    info("input user data = %s", args.user_data)
    info("input asset dir = %s", ', '.join(args.asset_dir))
    info("verify file reference = %s", args.verify_file_reference)
    info("output file reference list = %s", args.file_reference_list)
    verifier = MasterDataVerifier(args.asset_dir, args.verify_file_reference)
    verifier.load_master_data(args.input_master_schema, args.input_master_data)
    verifier.verify_master_data()
    if args.user_schema:
        verifier.load_user_data(args.user_schema, args.user_data)
        verifier.verify_user_data()
    if args.file_reference_list:
        verifier.generate_file_reference_list(args.file_reference_list)
    info("no error is detected")
    exit(0)

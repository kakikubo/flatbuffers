#! /usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import re
import codecs
import argparse
import json
import logging
from neo4jrestclient import client
from collections import OrderedDict
from logging import info, debug, warning, error

class DataImporter():
    def __init__(self, neo4j_url):
        self.gdb = client.GraphDatabase(neo4j_url)

        self.data_table_prefix = 'User' # FIXME
        self.schema = None
        self.data   = None

        self.key_map = OrderedDict()
        self.label_map = OrderedDict()
        self.reference_map = OrderedDict()
        self.file_reference_map = OrderedDict()

    def upper_camel_case(self, src):
        return src[0:1].upper() + src[1:]

    def lower_camel_case(self, src):
        return src[0:1].lower() + src[1:]

    def load_json(self, src_schema_file, src_data_file):
        with open(src_schema_file, 'r') as f:
            self.schema = json.load(f, object_pairs_hook=OrderedDict)
        with open(src_data_file, 'r') as f:
            self.data = json.load(f, object_pairs_hook=OrderedDict)
        return True

    def setup_reference(self):
        for table, schema in self.schema.iteritems():
            # skip enum schema
            if isinstance(schema, dict):
                continue

            string_keys = []
            self.reference_map[table]      = OrderedDict()
            self.file_reference_map[table] = OrderedDict()
            for sch in schema:
                name = sch['name']
                if sch['type'] == 'string':
                    string_keys.append(name)
                if sch.has_key('attribute') and sch['attribute']:
                    for k, v in sch['attribute'].iteritems():
                        if k == 'key':
                            # primary key
                            self.key_map[table] = name
                        elif k == 'label':
                            # label key
                            self.label_map[table] = name
                        elif k == 'file_reference':
                            # file reference
                            for fref, required in v.iteritems():
                                if not self.file_reference_map[table].has_key(name):
                                    self.file_reference_map[table][name] = {}
                                self.file_reference_map[table][name][fref] = required
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
                                if not self.reference_map[table].has_key(name):
                                    self.reference_map[table][name] = []
                                self.reference_map[table][name].append(refs)

            # select label key
            if not self.label_map.has_key(table):
                for key in string_keys:
                    if re.search(r'label', key, re.IGNORECASE):
                        self.label_map[table] = key
                        break
            if not self.label_map.has_key(table):
                if 'name' in string_keys:
                    self.label_map[table] = 'name'
                elif 'description' in string_keys:
                    self.label_map[table] = 'description'
                elif 'comment' in string_keys:
                    self.label_map[table] = 'comment'
            if not self.label_map.has_key(table):
                if len(string_keys) > 0:
                    self.label_map[table] = string_keys[0]
        return True

    def query_nodes(self, q):
        debug("QUERY: '%s'" % q)
        dest = []
        for container in self.gdb.query(q, returns=(client.Node, unicode)):
            dest.append(container[0])
        return dest

    def clear_gdb(self):
        q = "MATCH (n) DETACH DELETE n"
        debug("CLEAR GDB: %s" % q)
        return self.gdb.query(q)

    def create_data_node(self, label, table, item):
        # determine label
        if item.has_key('tag'):
            tag = u"{tag}@{table}".format(tag = item['tag'], table = table)
        elif self.label_map.has_key(table) and item.has_key(self.label_map[table]):
            tag = unicode(item[self.label_map[table]])
        else:
            tag = u"{id}@{table}".format(table = table, id = item[self.key_map[table]])

        # reverse table.value -> value.table
        splitted = tag.split('.')
        splitted.reverse()
        item['tag'] = '.'.join(splitted)  

        # create sub node for array or dict in item
        for k, v in item.iteritems():
            # FIXME too large and nested -> expand target item
            if isinstance(v, dict) or isinstance(v, list):
                return None

        debug("CREATE DATA NODE %s: %s" % (table, json.dumps(item, indent=2)))
        return label.create(**item)

    def create_data_nodes(self):
        for table, schema in self.schema.iteritems():
            table_key = self.lower_camel_case(re.sub(self.data_table_prefix, '', table))
            if not self.data.has_key(table_key):
                continue
            info("create data nodes: %s (%s)" % (table, table_key))

            #with self.gdb.transaction(for_query = True) as tx:
            table_data = self.data[table_key]
            label = self.gdb.labels.create(table)
            if isinstance(table_data, dict):
                self.create_data_node(label, table, table_data)
            elif isinstance(table_data, list):
                for item in table_data:
                    self.create_data_node(label, table, item)
            else:
                raise Exception("invalid data type in %s: %s" % (table, table_data))
        return True

    def create_data_relationships(self):
        for table, references in self.reference_map.iteritems():
            if not self.key_map.has_key(table):
                continue
            id_key    = self.key_map[table]
            reference = self.reference_map[table]
            info("create data relationships: %s" % table)

            relationships = []
            nodes = self.query_nodes('MATCH (n:`{label}`) RETURN n'.format(label = table))
            for node in nodes:
                for key, refs in reference.iteritems():
                    val = node.get(key, None)
                    if not val:
                        continue
                    for ref in refs:
                        id = '"'+val+'"' if type(val) in (unicode, str) else val
                        peers = self.query_nodes('MATCH (n:`{label}`) WHERE n.{key} = {id} RETURN n'.format(label = ref[0], key = ref[1], id = id))
                        for peer in peers:
                            #relation = u"{id}:{relation}".format(id = id, relation = '.'.join(ref))
                            relation = '.'.join(ref)
                            relationships.append([table, id, node, relation, peer])

            #with self.gdb.transaction(for_query = True) as tx:
            for table, id, node, relation, peer in relationships:
                debug("CREATE DATA RELATIONSHIP %s %s: %s" % (table, id, relation))
                node.relationships.create(relation, peer, id=id)
        return True

    def file_ref_label(self, table, fref):
        bname, ext = os.path.splitext(fref)
        return "{ext}@{table}".format(table = table, ext = ext[1:])

    def create_file_node(self, label, table, item, key, fref, required):
        if not item.has_key(key) or not item[key]:
            return None

        id = item[self.key_map[table]]
        path = fref.replace('{}', str(item[key])).format(**item).encode('utf-8')

        debug("CREATE FILE NODE %s %s: %s %s %s" % (table, id, key, path, required))
        return label.create(name = os.path.basename(path), key = key, path = path, required = required, id = id)

    def create_file_nodes(self):
        for table, schema in self.schema.iteritems():
            table_key = self.lower_camel_case(re.sub(self.data_table_prefix, '', table))
            if not self.data.has_key(table_key) or not self.file_reference_map.has_key(table):
                continue
            info("create file nodes: %s (%s)" % (table, table_key))

            #with self.gdb.transaction(for_query = True) as tx:
            table_data = self.data[table_key]
            for key, file_reference in self.file_reference_map[table].iteritems():
                for fref, required in file_reference.iteritems():
                    label = self.gdb.labels.create(self.file_ref_label(table, fref))
                    if isinstance(table_data, dict):
                        self.create_file_node(label, table, table_data, key, fref, required)
                    elif isinstance(table_data, list):
                        for item in table_data:
                            self.create_file_node(label, table, item, key, fref, required)
                    else:
                        raise Exception("invalid data type in %s: %s" % (table, table_data))
        return True

    def create_file_relationships(self):
        for table, schema in self.schema.iteritems():
            table_key = self.lower_camel_case(re.sub(self.data_table_prefix, '', table))
            if not self.data.has_key(table_key):
                continue
            info("create file relationships: %s" % table)

            relationships = []
            nodes = self.query_nodes('MATCH (n:`{label}`) RETURN n'.format(label = table))
            for node in nodes:
                for key, file_reference in self.file_reference_map[table].iteritems():
                    for fref, required in file_reference.iteritems():
                        id = node[self.key_map[table]]
                        id = '"'+id+'"' if type(id) in (unicode, str) else id
                        peers = self.query_nodes('MATCH (n:`{label}`) WHERE n.id = {id} RETURN n'.format(label = self.file_ref_label(table, fref), id = id))
                        for peer in peers:
                            relation = "{name}@{table}.{key}".format(name = peer['name'], table = table, key = key)
                            relationships.append([table, id, node, relation, peer])

            #with self.gdb.transaction(for_query = True) as tx:
            for table, id, node, relation, peer in relationships:
                debug("CREATE FILE RELATIONSHIP %s %s: %s" % (table, id, relation))
                node.relationships.create(relation, peer, id = id, name = peer['name'], key = peer['key'], path = peer['path'], required = peer['required'])
        return True

if __name__ == '__main__':
    neo4j_url_default = "http://neo4j:fflkms001@localhost:7474/db/data/"
    parser = argparse.ArgumentParser(description='import master|user data into neo4j database', epilog="""\
example:
    $ ./import_data.py master_derivatives/master_schema.json master_derivatives/master_data.json""")
    parser.add_argument('input_schema', metavar = 'xxx_schema.json', help = 'input (master|user) data schema json file')
    parser.add_argument('input_data',   metavar = 'xxx_data.json',   help = 'input (master|user) data json file')
    parser.add_argument('--neo4j-url', default = neo4j_url_default, help = 'neo4j server to connect. e.g. http://<username>:<password>@<host>:<port>/db/data')
    parser.add_argument('--log-level', help = 'log level (WARNING|INFO|DEBUG). default: INFO')
    args = parser.parse_args()
    logging.basicConfig(level = args.log_level or "INFO", format = '%(asctime)-15s %(levelname)s %(message)s')

    importer = DataImporter(args.neo4j_url)
    importer.load_json(args.input_schema, args.input_data)
    importer.setup_reference()

    importer.clear_gdb()
    importer.create_file_nodes()
    importer.create_data_nodes()
    importer.create_file_relationships()
    importer.create_data_relationships()

    exit(0)

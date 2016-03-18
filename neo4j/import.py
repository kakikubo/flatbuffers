#! /usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import re
import codecs
import argparse
import json
import logging
import tinycss
from neo4jrestclient import client
from collections import OrderedDict
from glob import glob
from logging import info, debug, warning, error

neo4j_url_default = "http://neo4j:fflkms001@localhost:7474/db/data/"
graphstyle_template_default = os.path.join(os.path.dirname(__file__), 'graphstyle.grass.template')

class Neo4jImporter():
    def __init__(self, neo4j_url, asset_dir):
        self.gdb = client.GraphDatabase(neo4j_url)
        self.asset_dir = asset_dir

        self.meta_table = '_meta' # FIXME
        self.data_table_prefix = 'User' # FIXME

        self.schema = None
        self.data   = None

        # schema map
        self.key_map            = OrderedDict()
        self.index_map          = OrderedDict()
        self.caption_map        = OrderedDict()
        self.reference_map      = OrderedDict()
        self.file_reference_map = OrderedDict()
        self.category_map       = OrderedDict()
        self.cost_map           = OrderedDict()
        self.color_map          = OrderedDict()

        # created items
        self.created_labels        = OrderedDict()
        self.created_nodes         = OrderedDict()
        self.created_indexes       = OrderedDict()
        self.created_relationships = OrderedDict()

        # css
        self.css_color_map      = OrderedDict()
        self.file_color_map     = OrderedDict()
        self.node_template = self.relationship_template = None
        self.static_css = []

    def setup_reference(self):
        for table, schema in self.schema.iteritems():
            # skip enum schema
            if isinstance(schema, dict):
                continue

            self.reference_map[table]      = OrderedDict()
            self.file_reference_map[table] = OrderedDict()
            for sch in schema:
                name = sch['name']
                if sch.has_key('attribute') and sch['attribute']:
                    for k, v in sch['attribute'].iteritems():
                        if k == 'key':
                            # primary key
                            self.key_map[table] = name
                        elif k == 'index':
                            # primary key
                            if not self.index_map.has_key(table):
                                self.index_map[table] = []
                            self.index_map[table].append(name)
                        elif k == 'caption':
                            self.caption_map[table] = name
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
                                r = ref.split('.')
                                if len(r) > 3:
                                    raise Exception("invalid reference definition: "+v)
                                if not self.reference_map[table].has_key(name):
                                    self.reference_map[table][name] = {}
                                r[0] = self.upper_camel_case(r[0]) # treat reference as Table Type
                                self.reference_map[table][name]['.'.join(r)] = required

        if self.schema.has_key(self.meta_table):
            for sch in self.schema[self.meta_table]:
                table = self.upper_camel_case(sch['name'])
                self.category_map[table] = sch['category']
                self.cost_map[table] = sch['cost']
                self.color_map[table] = sch['color']

        return True

    """
        Utilities
    """
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

    def clear_gdb(self):
        q = "MATCH (n) DETACH DELETE n"
        debug("CLEAR GDB: %s" % q)
        return self.gdb.query(q)

    def query_nodes(self, q):
        debug("QUERY: '%s'" % q)
        dest = []
        for container in self.gdb.query(q, returns=(client.Node, unicode)):
            dest.append(container[0])
        return dest

    def create_index(self, label, key):
        q = "CREATE INDEX ON :`{label}`({key})".format(label = label, key = key)
        debug("CREATE INDEX: '%s'" % q)
        return self.gdb.query(q)

    """
        Table nodes (schema)
    """
    def create_table_nodes(self):
        self.created_labels['table'] = []
        self.created_nodes['table'] = []
        #with self.gdb.transaction(for_query = True) as tx:
        for table, schema in self.schema.iteritems():
            if isinstance(schema, dict) or table == self.meta_table:
                continue
            info("create table nodes: %s" % table)

            label = self.gdb.labels.create('{table}:t'.format(table = table))
            self.created_labels['table'].append({'label': label})

            columns = OrderedDict()
            for sch in schema:
                columns[sch['name']] = sch['type']
            debug("CREATE TABLE NODE %s" % table)
            category = self.category_map[table] if self.category_map.has_key(table) else None
            cost = self.cost_map[table] if self.cost_map.has_key(table) else 0
            node = label.create(_table = table, _nodeType = 'table', _category = category, _cost = cost, **columns)
            self.created_nodes['table'].append({'node': node, 'label': label, 'caption': '_table'})

    def create_table_relationships(self):
        self.created_relationships['table'] = [];
        relationships = []
        for table, references in self.reference_map.iteritems():
            info("create table relationships: %s" % table)

            nodes = self.query_nodes('MATCH (n:`{table}:t`) RETURN n'.format(table = table))
            for node in nodes:
                for key, refs in references.iteritems():
                    for ref, required in refs.iteritems():
                        r = ref.split('.')
                        peers = self.query_nodes('MATCH (n:`{table}:t`) RETURN n'.format(table = r[0]))
                        for peer in peers:
                            relation = "{ref}:t".format(ref = ref)
                            relationships.append([table, key, node, peer, relation, required])

        #with self.gdb.transaction(for_query = True) as tx:
        for table, key, node, peer, relation, required in relationships:
            if not required:
                continue    # FIXME drop relationship for shortestPath
            debug("CREATE TABLE RELATIONSHIP %s %s: %s" % (table, key, relation))
            relationship = node.relationships.create(relation, peer, table = table, key = key, required = required, _relationType = 'table')
            self.created_relationships['table'].append({'relationship': relationship, 'relation': relation, 'caption': 'key', 'table': table})
        return True

    """
        Fref nodes (schema)
    """
    def create_fref_nodes(self):
        self.created_labels['fref'] = []
        self.created_nodes['fref'] = []
        #with self.gdb.transaction(for_query = True) as tx:
        fref_label_map = OrderedDict()
        for table, file_references in self.file_reference_map.iteritems():
            info("create fref nodes: %s" % table)
            for key, file_reference in file_references.iteritems():
                for fref, required in file_reference.iteritems():
                    bname, ext = os.path.splitext(fref)
                    if not fref_label_map.has_key(ext):
                        fref_label_map[ext] = self.gdb.labels.create('{ext}:f'.format(ext = ext))
                        self.created_labels['fref'].append({'label': fref_label_map[ext]})
                    label = fref_label_map[ext]
                    debug("CREATE FREF NODE %s %s: %s %s" % (table, key, fref, required))
                    node = label.create(table = table, key = key, extension = ext, 
                            name = os.path.basename(fref), path = fref, required = required, _cost = 0, _nodeType = 'fref')
                    self.created_nodes['fref'].append({'node': node, 'label': label, 'caption': 'path'})
        return True

    def create_fref_relationships(self):
        self.created_relationships['fref'] = [];
        relationships = []
        for table, schema in self.schema.iteritems():
            info("create fref relationships: %s" % table)

            nodes = self.query_nodes('MATCH (n:`{table}:t`) RETURN n'.format(table = table))
            for node in nodes:
                for key, file_reference in self.file_reference_map[table].iteritems():
                    for fref, required in file_reference.iteritems():
                        bname, ext = os.path.splitext(fref)
                        peers = self.query_nodes('MATCH (n:`{ext}:f`) WHERE n.table = "{table}" and n.path = "{path}" RETURN n'.format(ext = ext, table = table, path = fref))
                        for peer in peers:
                            relation = '{fref}:f'.format(fref = fref)
                            relationships.append([table, key, node, peer, relation, required])

        #with self.gdb.transaction(for_query = True) as tx:
        for table, key, node, peer, relation, required in relationships:
            debug("CREATE FREF RELATIONSHIP %s %s: %s" % (table, id, relation))
            relationship = node.relationships.create(relation, peer, key = key, required = required, _relationType = 'fref')
            self.created_relationships['fref'].append({'relationship': relationship, 'relation': relation, 'caption': 'key', 'table': table})
        return True

    """
        Data nodes (table data)
    """
    def create_data_node(self, label, table, item):
        # set caption
        if self.caption_map.has_key(table) and item.has_key(self.caption_map[table]):
            caption = unicode(item[self.caption_map[table]])
            # reverse table.id_name -> id_name.table for readability
            splitted = caption.split('.')
            splitted.reverse()
            caption = '.'.join(splitted)  
        elif item.has_key('name'):
            caption = unicode(item['name'])
        elif item.has_key('description'):
            caption = unicode(item['description'])
        elif item.has_key('comment'):
            caption = unicode(item['comment'])
        elif item.has_key('label'):
            caption = unicode(item['label'])
        else:
            caption = u"{id}@{table}".format(table = table, id = item[self.key_map[table]])

        # create sub node for array or dict in item
        for k, v in item.iteritems():
            # FIXME too large and nested -> expand target item
            if isinstance(v, dict) or isinstance(v, list):
                return None

        debug("CREATE DATA NODE %s: %s" % (table, json.dumps(item, indent=2)))
        category = self.category_map[table] if self.category_map.has_key(table) else None
        cost = self.cost_map[table] if self.cost_map.has_key(table) else 0
        node = label.create(_table = table, _caption = caption, _nodeType = 'data', _category = category, _cost = cost, **item)
        self.created_nodes['data'].append({'node': node, 'label': label, 'caption': '_caption'})
        return node

    def create_data_nodes(self):
        self.created_labels['data'] = []
        self.created_nodes['data'] = []
        #with self.gdb.transaction(for_query = True) as tx:
        for table, schema in self.schema.iteritems():
            table_key = self.lower_camel_case(re.sub(self.data_table_prefix, '', table))
            if not self.data.has_key(table_key):
                continue
            info("create data nodes: %s (%s)" % (table, table_key))

            #with self.gdb.transaction(for_query = True) as tx:
            table_data = self.data[table_key]
            label = self.gdb.labels.create(table)
            self.created_labels['data'].append({'label': label})

            if isinstance(table_data, dict):
                self.create_data_node(label, table, table_data)
            elif isinstance(table_data, list):
                for item in table_data:
                    self.create_data_node(label, table, item)
            else:
                raise Exception("invalid data type in %s: %s" % (table, table_data))
        return True

    def create_data_indexes(self):
        self.created_indexes['data'] = []
        for label in self.created_labels['data']:
            table = label['label']
            for key in ['_table', '_category', '_nodeType']:
                index = self.create_index(table, key)
                self.created_indexes['data'].append(index)
            if self.key_map.has_key(table):
                index = self.create_index(table, self.key_map[table])
                self.created_indexes['data'].append(index)
            if self.index_map.has_key(table):
                for name in self.index_map[table]:
                    index = self.create_index(table, name)
                    self.created_indexes['data'].append(index)
        return True

    def create_data_relationships(self):
        self.created_relationships['data'] = [];
        for table, references in self.reference_map.iteritems():
            if not self.key_map.has_key(table):
                continue
            id_key = self.key_map[table]
            info("create data relationships: %s" % table)

            relationships = []
            nodes = self.query_nodes('MATCH (n:`{label}`) RETURN n'.format(label = table))
            for node in nodes:
                for key, refs in references.iteritems():
                    val = node.get(key, None)
                    if not val:
                        continue
                    for ref, required in refs.iteritems():
                        r = ref.split('.')
                        id = '"'+val+'"' if type(val) in (unicode, str) else val
                        peers = self.query_nodes('MATCH (n:`{label}`) WHERE n.{key} = {id} RETURN n'.format(label = r[0], key = r[1], id = id))
                        for peer in peers:
                            relation = ref
                            relationships.append([table, key, id, node, peer, relation, required])

            #with self.gdb.transaction(for_query = True) as tx:
            for table, key, id, node, peer, relation, required in relationships:
                if not required:
                    continue    # FIXME drop relationship for shortestPath
                debug("CREATE DATA RELATIONSHIP %s %s: %s" % (table, id, relation))
                relationship = node.relationships.create(relation, peer, key = key, id = id, required = required, _relationType = 'data')
                self.created_relationships['data'].append({'relationship': relationship, 'relation': relation, 'caption': 'key', 'table': table})
        return True

    """
        File nodes (fref data)
    """
    def file_ref_path(self, fref, table, key, item):
        return fref.replace('{}', str(item[key])).format(**item).encode('utf-8')

    def file_real_path(self, path):
        return re.sub('^/', '', re.sub(self.asset_dir, '', path))

    def create_file_node(self, label, table, item, key, fref, required, file_node_map):
        if not item.has_key(key) or not item[key]:
            return file_node_map

        id = item[self.key_map[table]]
        path = self.file_ref_path(fref, table, key, item)
        bname, ext = os.path.splitext(path)

        for real_path in glob(os.path.join(self.asset_dir, path)):
            file_size = os.path.getsize(real_path)
            real_path = self.file_real_path(real_path)
            if file_node_map.has_key(real_path):
                continue
            
            debug("CREATE FILE NODE %s %s: %s %s %s (%s) %d" % (table, id, key, required, path, real_path, file_size))
            node = label.create(name = os.path.basename(real_path), extension = ext, 
                    table = table, key = key, path = path, real_path = real_path, file_size = file_size, 
                    required = required, id = id, _cost = 0, _nodeType = 'file')
            file_node_map[real_path] = node
            self.created_nodes['file'].append({'node': node, 'label': label, 'caption': 'name'})
        return file_node_map

    def create_file_nodes(self):
        self.created_labels['file'] = []
        self.created_nodes['file'] = []
        #with self.gdb.transaction(for_query = True) as tx:
        file_label_map = OrderedDict()
        file_node_map = OrderedDict()
        for table, schema in self.schema.iteritems():
            table_key = self.lower_camel_case(re.sub(self.data_table_prefix, '', table))
            if not self.data.has_key(table_key) or not self.file_reference_map.has_key(table):
                continue
            info("create file nodes: %s (%s)" % (table, table_key))

            #with self.gdb.transaction(for_query = True) as tx:
            table_data = self.data[table_key]
            for key, file_reference in self.file_reference_map[table].iteritems():
                for fref, required in file_reference.iteritems():
                    bname, ext = os.path.splitext(fref)
                    if not file_label_map.has_key(ext):
                        file_label_map[ext] = self.gdb.labels.create(ext)
                        self.created_labels['file'].append({'label': file_label_map[ext]})
                    label = file_label_map[ext]
                    if isinstance(table_data, dict):
                        file_node_map = self.create_file_node(label, table, table_data, key, fref, required, file_node_map)
                    elif isinstance(table_data, list):
                        for item in table_data:
                            file_node_map = self.create_file_node(label, table, item, key, fref, required, file_node_map)
                    else:
                        raise Exception("invalid data type in %s: %s" % (table, table_data))
        return True

    def create_file_indexes(self):
        self.created_indexes['file'] = []
        for label in self.created_labels['file']:
            ext = label['label']
            for key in ['name', 'extension', 'table', 'key', 'required', 'id', '_nodeType']:
                index = self.create_index(label, key)
                self.created_indexes['file'].append(index)
        return True

    def create_file_relationships(self):
        self.created_relationships['file'] = [];
        for table, schema in self.schema.iteritems():
            info("create file relationships: %s" % table)

            relationships = []
            nodes = self.query_nodes('MATCH (n:`{label}`) RETURN n'.format(label = table))
            for node in nodes:
                for key, file_reference in self.file_reference_map[table].iteritems():
                    for fref, required in file_reference.iteritems():
                        id = node[self.key_map[table]]
                        bname, ext = os.path.splitext(fref)
                        path = self.file_ref_path(fref, table, key, node.properties)
                        peers = self.query_nodes('MATCH (n:`{label}`) WHERE n.path = "{path}" RETURN n'.format(label = ext, path = path))
                        for peer in peers:
                            relation = self.file_real_path(peer['real_path'])
                            relationships.append([table, key, id, node, peer, relation, required])

            #with self.gdb.transaction(for_query = True) as tx:
            for table, key, id, node, peer, relation, required in relationships:
                debug("CREATE FILE RELATIONSHIP %s %s: %s" % (table, id, relation))
                properties = peer.properties
                relationship = node.relationships.create(relation, peer, 
                        key = key, id = id, required = required, 
                        _relationType = 'file', name = properties['name'], path = properties['path'])
                self.created_relationships['file'].append({'relationship': relationship, 'relation': relation, 'caption': 'key', 'table': table})
        return True

    """
        graphstyle.grass (css)
    """
    def css_str(self, rule, escape = False):
        delimiters = ('{{', '}}') if escape else ('{', '}')
        lines = []
        lines.append("%s %s" % (rule.selector.as_css(), delimiters[0]))
        for dec in rule.declarations:
            if dec.priority:
                lines.append("  %s: %s %s;" % (dec.name, dec.value.as_css(), dec.priority))
            else:
                lines.append("  %s: %s;" % (dec.name, dec.value.as_css()))
        lines.append(delimiters[1])
        return '\n'.join(lines)

    def get_color(self, key1, key2):
        color = 'gray'
        if self.color_map.has_key(key1):
            color = self.color_map[key1];
        elif self.color_map.has_key(key2):
            color = self.color_map[key2];
        elif self.file_color_map.has_key(key1):
            color = self.color_map[key1];
        elif self.file_color_map.has_key(key2):
            color = self.color_map[key2];
        if not self.css_color_map.has_key(color):
            color = 'gray'  # fallback
        return color

    def parse_css_template(self, template_path):
        # parse css template
        css_parser = tinycss.make_parser('page3')
        with open(template_path, 'r') as f:
            parsed = css_parser.parse_stylesheet(f.read());
            if parsed.errors:
                raise Exception("cannot parse graphstyle_template: %s" % parsed.errors)

        for rule in parsed.rules:
            selector = rule.selector.as_css()
            m1 = re.match(r'^color\.(.+)', selector)
            m2 = re.match(r'^file\.(.+)', selector)
            if m1:
                color = m1.group(1)
                self.css_color_map[color] = {}
                for dec in rule.declarations:
                    self.css_color_map[color][dec.name] = dec.value.as_css()
            elif m2:
                type = m2.group(1)
                self.file_color_map[type] = {}
                for dec in rule.declarations:
                    if dec.name == 'color':
                        self.file_color_map[type] = dec.value.as_css()
            elif selector == 'node.template':
                self.node_template = self.css_str(rule, True)
            elif selector == 'relationship.template':
                self.relationship_template = self.css_str(rule, True)
            else:
                self.static_css.append(self.css_str(rule))

    def generate_style(self, css_path, template_path):
        info("generate neo4j graph style: %s <- %s" % (css_path, template_path))
        self.parse_css_template(template_path)

        # output css
        written_nodes = {}
        written_relationships = {}
        with open(css_path, 'w') as f:
            f.write('\n\n'.join(self.static_css))
            f.write('\n\n')

            # node
            for node_type, nodes in self.created_nodes.iteritems():
                for c in nodes:
                    label = c['label']._label
                    if written_nodes.has_key(label):
                        continue

                    diameter = 50   # default 50px
                    if self.cost_map.has_key(label):
                        diameter += self.cost_map[label];
                    color = self.get_color(label, re.sub(':.+', '', label))
                    conf = self.css_color_map[color]

                    debug("write node grapthstyle: %s %s %s %s" % (label, c['caption'], diameter, color))
                    node_css = self.node_template.format(label = label, caption = c['caption'], diameter = diameter, **conf)
                    f.write(re.sub(r'\.template', '.'+label, node_css))
                    f.write('\n\n')

                    written_nodes[label] = True

            # relationship
            for relationship_type, relationships in self.created_relationships.iteritems():
                for c in relationships:
                    if written_relationships.has_key(c['relation']):
                        continue

                    table = c['table']
                    shaft_width = 2 # default 2px
                    if self.cost_map.has_key(table) and self.cost_map[table] > 0:
                        shaft_width += self.cost_map[table] / 10;
                    color = self.get_color(table, re.sub(':.+', '', table))
                    conf = {'shaft-width':  shaft_width}
                    conf.update(self.css_color_map[color])

                    debug("write relationship grapthstyle: %s %s %s %s" % (c['relation'], c['caption'], shaft_width, color))
                    relationship_css = self.relationship_template.format(relation = c['relation'], caption = c['caption'], **conf)
                    f.write(re.sub(r'\.template', '.'+c['relation'], relationship_css))
                    f.write('\n\n')

                    written_relationships[c['relation']] = True
        return True

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='import master|user data into neo4j database', epilog="""\
example:
    $ ./neo4j/import_data.py master_derivatives/master_schema.json master_derivatives/master_data.json kms_master_asset""")
    parser.add_argument('input_schema', metavar = 'xxx_schema.json',  help = 'input (master|user) data schema json file')
    parser.add_argument('input_data',   metavar = 'xxx_data.json',    help = 'input (master|user) data json file')
    parser.add_argument('asset_dir',    metavar = 'kms_master_asset', help = 'asset root dir')
    parser.add_argument('--css-path',   metavar = 'graphstyle.grass', help = 'generate Neo4j Graph Style Sheet')
    parser.add_argument('--neo4j-url',  default = neo4j_url_default, help = 'neo4j server to connect. e.g. http://<username>:<password>@<host>:<port>/db/data')
    parser.add_argument('--graphstyle-template', default = graphstyle_template_default, help = 'graphstyle.grass template file')
    parser.add_argument('--log-level',  help = 'log level (WARNING|INFO|DEBUG). default: INFO')
    args = parser.parse_args()
    logging.basicConfig(level = args.log_level or "INFO", format = '%(asctime)-15s %(levelname)s %(message)s')

    importer = Neo4jImporter(args.neo4j_url, args.asset_dir)
    importer.load_json(args.input_schema, args.input_data)
    importer.setup_reference()

    importer.clear_gdb()

    # schema
    importer.create_table_nodes()
    importer.create_fref_nodes()
    importer.create_table_relationships()
    importer.create_fref_relationships()

    # data
    importer.create_file_nodes()
    importer.create_data_nodes()
    importer.create_file_relationships()
    importer.create_data_relationships()

    # index
    importer.create_file_indexes()
    importer.create_data_indexes()

    if args.css_path:
        importer.generate_style(args.css_path, args.graphstyle_template)

    exit(0)

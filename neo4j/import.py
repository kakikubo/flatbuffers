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
from deepdiff import DeepDiff 
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

    def query_nodes(self, q):
        debug("QUERY NODES: '%s'" % q)
        dest = []
        for node, in self.gdb.query(q, returns=(client.Node)):
            dest.append(node)
        return dest

    def query_node_pairs(self, q):
        debug("QUERY NODE PAIRS: '%s'" % q)
        dest = []
        for node1, node2 in self.gdb.query(q, returns=(client.Node, client.Node)):
            dest.append([node1, node2])
        return dest

    def query_node_map(self, node_type, key, sub_key_map = False):
        q = 'MATCH (n {_nodeType: "%s"}) RETURN n' % node_type
        debug("QUERY NODE MAP: '%s'" % q)

        node_map = {}
        for node, in self.gdb.query(q, returns=(client.Node)):
            val = node.properties[key]
            if sub_key_map:
                if not self.key_map.has_key(val):
                    continue
                sub_key = self.key_map[val]
                sub_val = node.properties[sub_key]
                if not node_map.has_key(val):
                    node_map[val] = OrderedDict()
                node_map[val][sub_val] = node
            else:
                if not node_map.has_key(val):
                    node_map[val] = []
                node_map[val].append(node)
        return node_map

    def query_labels(self, node_type):
        q = 'MATCH (n {_nodeType: "%s"}) RETURN DISTINCT labels(n)' % node_type
        debug("QUERY LABELS: '%s'" % q)
        dest = {}
        for labels, in self.gdb.query(q, data_contents=True):
            for label in labels:
                dest[label] = True
        return dest.keys()

    def query_relationship_map(self, node_type):
        q = 'MATCH ()-[r {_relationType: "%s"}]-() RETURN r' % node_type
        debug("QUERY RELATIONSHIP MAP: '%s'" % q)

        relationship_map = {}
        for relationship, in self.gdb.query(q, returns=(client.Relationship)):
            val = relationship.properties['_id']
            if not relationship_map.has_key(val):
                relationship_map[val] = OrderedDict()
            relationship_map[val] = relationship
        return relationship_map

    def query_relationship_types(self, relationship_type):
        q = 'MATCH ()-[r {_relationType: "%s"}]-() RETURN DISTINCT type(r), r.table' % relationship_type
        debug("QUERY RELATIONSHIP TYPES: '%s'" % q)
        dest = {}
        for type, table in self.gdb.query(q, data_contents=True):
            dest[type] = table
        return dest

    def create_index(self, label, key):
        q = "CREATE INDEX ON :`{label}`({key})".format(label = label, key = key)
        debug("CREATE INDEX: '%s'" % q)
        return self.gdb.query(q)

    def delete_nodes(self, q):
        debug("DELETE NODES: '%s'" % q)
        return self.gdb.query(q)

    def delete_relationships(self, relation_type, _id):
        q = 'MATCH ()-[r {_relationType: "%s", _id: "%s"}]-() DELETE r' % (relation_type, _id)
        debug("DELETE RELATIONSHIPS: '%s'" % q)
        return self.gdb.query(q)

    def clear_gdb(self):
        q = "MATCH (n) DETACH DELETE n"
        debug("CLEAR GDB: %s" % q)
        return self.gdb.query(q)

    """
        Table nodes (schema)
    """

    def create_table_nodes(self):
        info("create table nodes")
        table_node_map = self.query_node_map('table', '_table')

        # create or update table nodes
        for table, schema in self.schema.iteritems():
            if isinstance(schema, dict) or table == self.meta_table:
                continue
            info("create table nodes: %s" % table)

            # setup node properties
            properties = {}
            for sch in schema:
                properties[sch['name']] = sch['type']
            category = self.category_map[table] if self.category_map.has_key(table) else None
            cost = self.cost_map[table] if self.cost_map.has_key(table) else 0
            properties.update({
                u'_table': unicode(table), 
                u'_nodeType': u'table', 
                u'_category': unicode(category), 
                u'_cost': cost
            })

            # update or create
            nodes = table_node_map[table] if table_node_map.has_key(table) else None
            if not nodes:
                label = self.gdb.labels.create('{table}:t'.format(table = table))

                debug("CREATE TABLE NODE %s" % table)
                node = label.create(**properties)
            else:
                diff = DeepDiff(nodes[0].properties, properties, ignore_order = True)
                if diff:
                    debug("UPDATE TABLE NODE: %s (%s)" % (table, diff.changes))
                    nodes[0].properties = properties
                else:
                    debug("STABLE TABLE NODE: %s" % table)
                del table_node_map[table]   # mark updated

        # deleted nodes
        for table, nodes in table_node_map.iteritems():
            self.delete_nodes("MATCH (n:`{table}:t`) DETACH DELETE n".format(table = table))
        return True

    def create_table_relationships(self):
        info("create table relationships: begin")
        table_relationship_map = self.query_relationship_map('table')

        # create or update table relationships
        for table, references in self.reference_map.iteritems():
            info("create table relationships: %s" % table)

            for key, refs in references.iteritems():
                for ref, required in refs.iteritems():
                    # setup relationship properties
                    r = ref.split('.')
                    relation = "{ref}:t".format(ref = ref)
                    _id = u'{table}-{key}-{ref}'.format(table = table, key = key, ref = ref)
                    properties = {
                        u'_id': _id, 
                        u'table': unicode(table), 
                        u'key': unicode(key), 
                        u'required': required, 
                        u'_relationType': u'table'
                    }

                    # create or update
                    if not table_relationship_map.has_key(_id):
                        pairs = self.query_node_pairs('MATCH (n:`{table}:t`), (p:`{peer}:t`) RETURN n, p'.format(table = table, peer = r[0]))
                        if pairs:
                            debug("CREATE TABLE RELATIONSHIP (%s.%s)-[%s]-(%s)" % (table, key, relation, r[0]))
                        for node, peer in pairs:
                            relationship = node.relationships.create(relation, peer, **properties)
                    else:
                        relationship = table_relationship_map[_id]
                        diff = DeepDiff(relationship.properties, properties, ignore_order = True)
                        if diff:
                            debug("UPDATE TABLE RELATIONSHIP (%s.%s)-[%s]-(%s): %s" % (table, key, relation, r[0], diff.changes))
                            relationship.properties = properties
                        else:
                            debug("STABLE TABLE RELATIONSHIP (%s.%s)-[%s]-(%s)" % (table, key, relation, r[0]))
                        del table_relationship_map[_id]  # mark updated

        # deleted relationships
        for _id, relationships in table_relationship_map.iteritems():
            self.delete_relationships('table', _id)
        return True

    """
        Fref nodes (schema)
    """
    def create_fref_nodes(self):
        info("create fref nodes: begin")
        fref_node_map = self.query_node_map('fref', 'id')
        debug(fref_node_map)

        # create or update file nodes
        fref_label_map = OrderedDict()
        for table, file_references in self.file_reference_map.iteritems():
            info("create fref nodes: %s" % table)
            for key, file_reference in file_references.iteritems():
                for fref, required in file_reference.iteritems():
                    # setup node properties
                    bname, ext = os.path.splitext(fref)
                    id = u'{table}-{key}-{fref}'.format(table = table, key = key, fref = fref)
                    properties = {
                        u'id': id,
                        u'table': unicode(table), 
                        u'key': unicode(key), 
                        u'extension': unicode(ext), 
                        u'name': unicode(os.path.basename(fref)), 
                        u'path': unicode(fref), 
                        u'required': required, 
                        u'_cost': 0, 
                        u'_nodeType': u'fref'
                    }

                    # update or create
                    nodes = fref_node_map[id] if fref_node_map.has_key(id) else None
                    if not nodes:
                        # FIXME label map
                        if not fref_label_map.has_key(ext):
                            fref_label_map[ext] = self.gdb.labels.create('{ext}:f'.format(ext = ext))
                        label = fref_label_map[ext]

                        debug("CREATE FREF NODE %s %s: %s %s" % (table, key, fref, required))
                        node = label.create(**properties)
                    else:
                        diff = DeepDiff(nodes[0].properties, properties, ignore_order = True)
                        if diff:
                            debug("UPDATE FREF NODE: %s (%s)" % (table, diff.changes))
                            nodes[0].properties = properties
                        else:
                            debug("STABLE FREF NODE: %s" % table)
                        del fref_node_map[id]   # mark updated

        # deleted nodes
        for id, nodes in fref_node_map.iteritems():
            self.delete_nodes('MATCH (n: {id: "%s", _nodeType: "fref"}) DETACH DELETE n' % id)
        return True

    def create_fref_relationships(self):
        info("create fref relationships: begin")
        fref_relationship_map = self.query_relationship_map('fref')

        # create or update fref relationships
        for table, schema in self.schema.iteritems():
            if not self.file_reference_map.has_key(table):
                continue
            info("create fref relationships: %s" % table)

            for key, file_reference in self.file_reference_map[table].iteritems():
                for fref, required in file_reference.iteritems():
                    relation = '{fref}:f'.format(fref = fref)
                    bname, ext = os.path.splitext(fref)
                    _id = u'{table}-{key}-{fref}'.format(table = table, key = key, fref = fref)
                    properties = {
                        u'_id': _id,
                        u'key': unicode(key), 
                        u'required': required, 
                        u'_relationType': u'fref'
                    }

                    if not fref_relationship_map.has_key(_id):
                        pairs = self.query_node_pairs('MATCH (n:`{table}:t`), (p:`{ext}:f`) RETURN n, p'.format(table = table, ext = ext))
                        if pairs:
                            debug("CREATE FREF RELATIONSHIP (%s.%s)-[%s]-(%s)" % (table, key, relation, ext))
                        for node, peer in pairs:
                            relationship = node.relationships.create(relation, peer, **properties)
                    else:
                        relationship = fref_relationship_map[_id]
                        diff = DeepDiff(relationship.properties, properties, ignore_order = True)
                        if diff:
                            debug("UPDATE FREF RELATIONSHIP (%s.%s)-[%s]-(%s): %s" % (table, key, relation, ext, diff.changes))
                            relationship.properties = properties
                        else:
                            debug("STABLE FREF RELATIONSHIP (%s.%s)-[%s]-(%s)" % (table, key, relation, ext))
                        del fref_relationship_map[_id]  # mark updated

        # deleted relationships
        for _id, relationships in fref_relationship_map.iteritems():
            self.delete_relationships('fref', _id)
        return True

    """
        Data nodes (table data)
    """
    def create_data_node(self, label, table, item, data_node_map):
        # create sub node for array or dict in item
        for k, v in item.iteritems():
            # FIXME too large and nested -> expand target item
            if isinstance(v, dict) or isinstance(v, list):
                return data_node_map

        # setup properties
        id = item[self.key_map[table]]
        category = self.category_map[table] if self.category_map.has_key(table) else None
        cost = self.cost_map[table] if self.cost_map.has_key(table) else 0
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
            caption = u"{id}@{table}".format(table = table, id = id)
        properties = {
            u'_table': unicode(table), 
            u'_caption': unicode(caption), 
            u'_nodeType': u'data', 
            u'_category': unicode(category), 
            u'_cost': cost
        }
        properties.update(item)

        # update or create
        if not data_node_map.has_key(table) or not data_node_map[table].has_key(id):
            debug("CREATE DATA NODE %s.%s: %s" % (table, id, json.dumps(item, indent=2)))
            node = label.create(**properties)
        else:
            node = data_node_map[table][id]
            diff = DeepDiff(node.properties, properties, ignore_order = True)
            if diff:
                debug("UPDATE DATA NODE %s.%s: %s" % (table, id, diff.changes))
                node.properties = properties
            else:
                debug("STABLE DATA NODE %s.%s" % (table, id))
            del data_node_map[table][id]   # mark updated

        return data_node_map

    def create_data_nodes(self):
        info("create data nodes: begin")
        data_node_map = self.query_node_map('data', '_table', True)

        # create or update table nodes
        for table, schema in self.schema.iteritems():
            table_key = self.lower_camel_case(re.sub(self.data_table_prefix, '', table))
            if not self.data.has_key(table_key):
                continue
            info("create data nodes: %s (%s)" % (table, table_key))
            table_data = self.data[table_key]

            label = self.gdb.labels.create(table)

            if isinstance(table_data, dict):
                data_node_map = self.create_data_node(label, table, table_data, data_node_map)
            elif isinstance(table_data, list):
                for item in table_data:
                    data_node_map = self.create_data_node(label, table, item, data_node_map)
            else:
                raise Exception("invalid data type in %s: %s" % (table, table_data))

            # deleted nodes
            if data_node_map.has_key(table):
                for id, nodes in data_node_map[table].iteritems():
                    self.delete_nodes("MATCH (n:`%s` {id: %d}) DETACH DELETE n" % (table, id))
        return True

    def create_data_indexes(self):
        info("create data indexes: begin")
        for table in self.query_labels('data'):
            for key in ['_table', '_category', '_nodeType']:
                index = self.create_index(table, key)
            if self.key_map.has_key(table):
                index = self.create_index(table, self.key_map[table])
            if self.index_map.has_key(table):
                for name in self.index_map[table]:
                    index = self.create_index(table, name)
        return True

    def create_data_relationships(self):
        info("create data relationships: begin")
        data_node_map = self.query_node_map('data', '_table', True)
        data_relationship_map = self.query_relationship_map('data')
        org_data_relationship_map = {}
        for key in data_relationship_map.keys():
            org_data_relationship_map[key] = True

        for table, references in self.reference_map.iteritems():
            if not self.key_map.has_key(table) or not data_node_map.has_key(table):
                continue
            id_key = self.key_map[table]
            info("create data relationships: %s" % table)

            for key, refs in references.iteritems():
                for ref, required in refs.iteritems():
                    relation = ref
                    r = ref.split('.')

                    # map peers by referenced key
                    peer_node_map = OrderedDict()
                    if data_node_map.has_key(r[0]):
                        for peer_id, peer in data_node_map[r[0]].iteritems():
                            peer_node_map[peer.properties[r[1]]] = peer

                    # create or update data relationships for target table
                    for id, node in data_node_map[table].iteritems():
                        _id = u'{table}-{key}-{ref}-{id}'.format(table = table, key = key, ref = ref, id = id)
                        peer_val = node.properties[key]
                        if not peer_node_map.has_key(peer_val):
                            continue
                        peer = peer_node_map[peer_val]
                        peer_id = peer.properties[self.key_map[r[0]]]
                        properties = {
                            u'_id': _id,
                            u'name': ref,
                            u'table': table,
                            u'key': key, 
                            u'id': id,
                            u'peerTable': r[0],
                            u'peerKey': r[1],
                            u'peerId': peer_id,
                            u'required': required, 
                            u'_relationType': u'data'
                        }

                        if not data_relationship_map.has_key(_id):
                            debug("CREATE DATA RELATIONSHIP (%s {id: %s, %s: %s})-[%s {_id: %s}]-(%s {id: %s})" % (table, id, key, peer_val, relation, _id, ref, peer_id))
                            relationship = node.relationships.create(relation, peer, **properties)
                            data_relationship_map[_id] = relationship
                        else:
                            relationship = data_relationship_map[_id]
                            diff = DeepDiff(relationship.properties, properties, ignore_order = True)
                            if diff:
                                debug("UPDATE DATA RELATIONSHIP (%s {id: %s, %s: %s})-[%s {_id: %s}]-(%s {id: %s}): %s" % (table, id, key, peer_val, relation, _id, ref, peer_id, diff.changes))
                                relationship.properties = properties
                            else:
                                debug("STABLE DATA RELATIONSHIP (%s {id: %s, %s: %s})-[%s {_id: %s}]-(%s {id: %s})" % (table, id, key, peer_val, relation, _id, ref, peer_id))
                            if org_data_relationship_map.has_key(_id):
                                del org_data_relationship_map[_id]  # mark updated

        # deleted relationships
        for _id in org_data_relationship_map.keys():
            self.delete_relationships('data', _id)
        return True

    """
        File nodes (fref data)
    """
    def file_ref_path(self, fref, table, key, item):
        return fref.replace('{}', str(item[key])).format(**item).encode('utf-8')

    def file_real_path(self, path):
        return re.sub('^/', '', re.sub(self.asset_dir, '', path))

    def create_file_node(self, label, table, item, key, fref, required, file_node_map, org_file_node_map):
        if not item.has_key(key) or not item[key]:
            return file_node_map

        path = self.file_ref_path(fref, table, key, item)
        for real_path in glob(os.path.join(self.asset_dir, path)):
            bname, ext = os.path.splitext(real_path)
            # setup properties
            file_size = os.path.getsize(real_path)
            real_path = self.file_real_path(real_path)
            properties = {
                u'name': unicode(os.path.basename(real_path)), 
                u'extension': unicode(ext), 
                u'path': unicode(path), 
                u'realPath': unicode(real_path), 
                u'fileSize': unicode(file_size), 
                u'required': required, 
                u'_cost': 0, 
                u'_nodeType': u'file'
            }
            
            # update or create
            if not file_node_map.has_key(real_path):
                debug("CREATE FILE NODE %s: %s %s %s (%s) %d" % (table, key, required, path, real_path, file_size))
                node = label.create(**properties)
                file_node_map[real_path] = [node]
            else:
                node = file_node_map[real_path][0]
                diff = DeepDiff(node.properties, properties, ignore_order = True)
                if diff:
                    debug("UPDATE FILE NODE %s: %s %s %s (%s) %d: %s" % (table, key, required, path, real_path, file_size, diff.changes))
                    node.properties = properties
                else:
                    debug("STABLE FILE NODE %s: %s %s %s (%s) %d" % (table, key, required, path, real_path, file_size))
                if org_file_node_map.has_key(real_path):
                    del org_file_node_map[real_path] # mark updated
        return file_node_map

    def create_file_nodes(self):
        info("create file nodes: begin")
        file_node_map = self.query_node_map('file', 'realPath')
        org_file_node_map = {}
        for key in file_node_map.keys():
            org_file_node_map[key] = True

        # create or update file nodes
        file_label_map = OrderedDict()
        processed_file_node_map = OrderedDict()
        for table, schema in self.schema.iteritems():
            table_key = self.lower_camel_case(re.sub(self.data_table_prefix, '', table))
            if not self.data.has_key(table_key) or not self.file_reference_map.has_key(table):
                continue
            info("create file nodes: %s (%s)" % (table, table_key))

            table_data = self.data[table_key]
            for key, file_reference in self.file_reference_map[table].iteritems():
                for fref, required in file_reference.iteritems():
                    bname, ext = os.path.splitext(fref)

                    if not file_label_map.has_key(ext):
                        file_label_map[ext] = self.gdb.labels.create(ext)
                    label = file_label_map[ext]

                    if isinstance(table_data, dict):
                        file_node_map = self.create_file_node(label, table, table_data, key, fref, required, file_node_map, org_file_node_map)
                    elif isinstance(table_data, list):
                        for item in table_data:
                            file_node_map = self.create_file_node(label, table, item, key, fref, required, file_node_map, org_file_node_map)
                    else:
                        raise Exception("invalid data type in %s: %s" % (table, table_data))

        # deleted nodes
        for real_path in org_file_node_map.keys():
            self.delete_nodes('MATCH (n {_nodeType: "file", realPath: "%s"}) DETACH DELETE n' % real_path)
        return True

    def create_file_indexes(self):
        info("create file indexes: begin")
        for ext in self.query_labels('file'):
            for key in ['name', 'extension', 'path', 'realPath', 'required', '_nodeType']:
                index = self.create_index(ext, key)
        return True

    def create_file_relationships(self):
        info("create file relatioships: begin")
        data_node_map = self.query_node_map('data', '_table', True)
        file_node_map = self.query_node_map('file', 'realPath')
        file_relationship_map = self.query_relationship_map('file')
        org_file_relationship_map = {}
        for key in file_relationship_map.keys():
            org_file_relationship_map[key] = True

        for table, schema in self.schema.iteritems():
            info("create file relationships: %s" % table)
            if not self.file_reference_map.has_key(table):
                continue

            for key, file_reference in self.file_reference_map[table].iteritems():
                for fref, required in file_reference.iteritems():
                    for id, node in data_node_map[table].iteritems():
                        path = self.file_ref_path(fref, table, key, node.properties)
                        for real_path in glob(os.path.join(self.asset_dir, path)):
                            real_path = self.file_real_path(real_path)
                            if not file_node_map.has_key(real_path):
                                continue
                            for peer in file_node_map[real_path]:
                                _id = "{table}-{key}-{id}-{real_path}".format(table = table, key = key, id = id, real_path = peer.properties['realPath'])
                                relation = self.file_real_path(peer.properties['realPath'])
                                properties = {
                                    u'key': unicode(key), 
                                    u'id': id,
                                    u'_id': unicode(_id), 
                                    u'required': required, 
                                    u'_relationType': u'file', 
                                    u'name': peer.properties['name'], 
                                    u'path': peer.properties['path']
                                }
                                if not file_relationship_map.has_key(_id):
                                    debug("CREATE FILE RELATIONSHIP (%s {id: %s})-[%s {_id: %s}]-(%s {path: %s})" % (table, id, relation, _id, fref, path))
                                    relationship = node.relationships.create(relation, peer, **properties)
                                    file_relationship_map[_id] = relationship
                                else:
                                    relationship = file_relationship_map[_id]
                                    diff = DeepDiff(relationship.properties, properties, ignore_order = True)
                                    if diff:
                                        debug("UPDATE FILE RELATIONSHIP (%s {id: %s})-[%s {_id: %s}]-(%s {path: %s}): %s" % (table, id, relation, _id, fref, path, diff.changes))
                                        relationship.properties = properties
                                    else:
                                        debug("STABLE FILE RELATIONSHIP (%s {id: %s})-[%s {_id: %s}]-(%s {path: %s})" % (table, id, relation, _id, fref, path))
                                    if org_file_relationship_map.has_key(_id):
                                        del org_file_relationship_map[_id] # mark updated

        # deleted relationships
        for _id in org_file_relationship_map.keys():
            self.delete_relationships('file', _id)
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
        with open(css_path, 'w') as f:
            f.write('\n\n'.join(self.static_css))
            f.write('\n\n')

            # node
            node_caption_map = {
                'table': '_table',
                'fref': 'path',
                'data': '_caption',
                'file': 'name',
            }
            for node_type, caption in node_caption_map.iteritems():
                for label in self.query_labels(node_type):
                    diameter = 50   # default 50px
                    if self.cost_map.has_key(label):
                        diameter += self.cost_map[label];
                    color = self.get_color(label, re.sub(':.+', '', label))
                    conf = self.css_color_map[color]

                    debug("write node grapthstyle: %s %s %s %s" % (label, caption, diameter, color))
                    node_css = self.node_template.format(label = label, caption = caption, diameter = diameter, **conf)
                    f.write(re.sub(r'\.template', '.'+label, node_css))
                    f.write('\n\n')

            # relationship
            relationship_caption_map = {
                'table': 'key',
                'fref':  'key',
                'data':  'name',
                'file':  'name',
            }
            for relationship_type, caption in relationship_caption_map.iteritems():
                for relation, table in self.query_relationship_types(relationship_type).iteritems():
                    shaft_width = 2 # default 2px
                    color = 'gray'
                    if table:
                        if self.cost_map.has_key(table) and self.cost_map[table] > 0:
                            shaft_width += self.cost_map[table] / 10;
                        color = self.get_color(table, re.sub(':.+', '', table))
                    conf = {'shaft-width':  shaft_width}
                    conf.update(self.css_color_map[color])

                    debug("write relationship grapthstyle: %s %s %s %s" % (relation, caption, shaft_width, color))
                    relationship_css = self.relationship_template.format(relation = relation, caption = caption, **conf)
                    f.write(re.sub(r'\.template', '.'+relation, relationship_css))
                    f.write('\n\n')
        return True

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='import master|user data into neo4j database', epilog="""\
example:
    $ ./neo4j/import.py master_derivatives/master_schema.json master_derivatives/master_data.json kms_master_asset""")
    parser.add_argument('input_schema', metavar = 'xxx_schema.json',  help = 'input (master|user) data schema json file')
    parser.add_argument('input_data',   metavar = 'xxx_data.json',    help = 'input (master|user) data json file')
    parser.add_argument('asset_dir',    metavar = 'kms_master_asset', help = 'asset root dir')
    parser.add_argument('--rebuild',    action = 'store_true', default = False, help = 'rebuild all data after clean up db')
    parser.add_argument('--css-path',   metavar = 'graphstyle.grass', help = 'generate Neo4j Graph Style Sheet')
    parser.add_argument('--neo4j-url',  default = neo4j_url_default, help = 'neo4j server to connect. e.g. http://<username>:<password>@<host>:<port>/db/data')
    parser.add_argument('--graphstyle-template', default = graphstyle_template_default, help = 'graphstyle.grass template file')
    parser.add_argument('--log-level',  help = 'log level (WARNING|INFO|DEBUG). default: INFO')
    args = parser.parse_args()
    logging.basicConfig(level = args.log_level or "INFO", format = '%(asctime)-15s %(process)d %(levelname)s %(message)s')

    importer = Neo4jImporter(args.neo4j_url, args.asset_dir)
    importer.load_json(args.input_schema, args.input_data)
    importer.setup_reference()

    if args.rebuild:
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

    # reconstruct index
    if args.rebuild:
        importer.create_file_indexes()
        importer.create_data_indexes()

    if args.css_path:
        importer.generate_style(args.css_path, args.graphstyle_template)

    exit(0)

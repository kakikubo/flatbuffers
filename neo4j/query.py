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
from glob import glob
from logging import info, debug, warning, error

neo4j_url_default = "http://neo4j:fflkms001@localhost:7474/db/data/"

class Neo4jQuery():
    def __init__(self, neo4j_url):
        self.gdb = client.GraphDatabase(neo4j_url)

    def query(self, q):
        info("QUERY: \n%s" % q)
        dest = []
        for container in self.gdb.query(q, data_contents=True):
            dest.append(container)
        return dest

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='import master|user data into neo4j database', epilog="""\
example:
    $ ./neo4j/import_data.py master_derivatives/master_schema.json master_derivatives/master_data.json kms_master_asset""")
    parser.add_argument('input_cypher', metavar = 'xxx.cypher',  help = 'input cypher file')
    parser.add_argument('output_json',  metavar = 'xxx.json', help = 'output json file')
    parser.add_argument('--aggrigate',  action = 'store_true', default = False, help = 'build map by most left key')
    parser.add_argument('--neo4j-url',  default = neo4j_url_default, help = 'neo4j server to connect. e.g. http://<username>:<password>@<host>:<port>/db/data')
    parser.add_argument('--log-level',  help = 'log level (WARNING|INFO|DEBUG). default: INFO')
    args = parser.parse_args()
    logging.basicConfig(level = args.log_level or "INFO", format = '%(asctime)-15s %(levelname)s %(message)s')

    query = Neo4jQuery(args.neo4j_url)
    cypher = ''
    with open(args.input_cypher, 'r') as f:
        cypher = f.read()
    data = query.query(cypher)

    if args.aggrigate:
        aggrigated = OrderedDict()
        for d in data:
            key = d[0]
            if not aggrigated.has_key(key):
                aggrigated[key] = []
            if len(d) > 2:
                aggrigated[key].append(d[1:])
            else:
                aggrigated[key].append(d[1])    # flatten
        info("aggrigated by %d items" % len(aggrigated))
        data = aggrigated

    with open(args.output_json, 'w') as f:
        json.dump(data, f, indent=2)

    exit(0)

#! /usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import json
import codecs
import logging
from logging import info, warning, debug
from collections import OrderedDict

def strip_json(src_json, dest_json, bundle_keys_json):
    src = bundle_keys = OrderedDict()
    with open(src_json, 'r') as f:
        src = json.load(f, object_pairs_hook=OrderedDict)
    with open(bundle_keys_json, 'r') as f:
        bundle_keys = json.load(f, object_pairs_hook=OrderedDict)
    info("bundled keys: '%s'" % "', '".join(bundle_keys))

    data = OrderedDict()
    for key, d in src.iteritems():
        if key in bundle_keys:
            data[key] = d
        elif isinstance(d, list):
            data[key] = []
        elif isinstance(d, dict):
            data[key] = {}
    
    with codecs.open(dest_json, "w") as f:
        dest = json.dumps(data, ensure_ascii = False, indent = 4)
        f.write(dest.encode("utf-8"))
    return True

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='strip master_data.json for bundled master dat', epilog="""\
example:
    $ ./strip_master_json.py asset/master_derivatives/master_data.json asset/master_derivatives/master_data_bundled.json asset/distribution/master_data_bundled_keys.json""")

    parser.add_argument('src_json', metavar='src.json', help='input json file')
    parser.add_argument('dest_json', metavar='dest.json', help='output json file')
    parser.add_argument('bundle_keys_json', metavar='bundle_list.json', help='filtering keys list by json flat array')
    parser.add_argument('--log-level', help = 'log level (WARNING|INFO|DEBUG). default: INFO')
    args = parser.parse_args()
    logging.basicConfig(level = args.log_level or "INFO", format = '%(asctime)-15s %(process)d %(levelname)s %(message)s')

    info("input master data json file =  %s" % args.src_json)
    info("output master data json file =  %s" % args.dest_json)
    strip_json(args.src_json, args.dest_json, args.bundle_keys_json)
    exit(0)

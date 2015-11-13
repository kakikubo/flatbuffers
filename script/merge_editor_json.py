#! /usr/bin/python
# -*- coding: utf-8 -*-

import argparse
import os
import re
import json
from collections import OrderedDict
import logging
from logging import info, warning, debug
from glob import glob

def merge_editor_files(src_file, dest_file, editor_files):
    with open(src_file, 'r') as f:
        json_data = json.loads(f.read(), object_pairs_hook=OrderedDict)

    for editor_file in editor_files:
        info("merge %s -> %s" % (os.path.basename(editor_file), os.path.basename(src_file)))
        with open(editor_file, 'r') as f:
            editor_json_data = json.loads(f.read(), object_pairs_hook=OrderedDict)
        for key in editor_json_data:
            data = editor_json_data[key]
            if '_' in key:
                a = key.split('_')
                key = a[0]
                if a[1] == "item":
                    if not key in json_data:
                        editor_json_data[key] = []
                    json_data[key].append(data)
            else:
                json_data[key] = data

    with open(dest_file, 'w') as f:
        j = json.dumps(json_data, ensure_ascii = False, indent = 4)
        f.write(j.encode("utf-8"))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='merge editor data or schema json files to master json', epilog="""\
example:
    $ ./merge_editor_json.py kms_master_asset/master_derivative/master_schema.json kms_hoge_asset/editor_schema/editor_schema.json""")

    parser.add_argument('master_json', help='src and dest master {schema|data} file')
    parser.add_argument('editor_jsons', default = [], nargs='*', help = 'source editor {schema|data} files')
    parser.add_argument('--log-level', help = 'log level (WARNING|INFO|DEBUG). default: INFO')
    args = parser.parse_args()
    logging.basicConfig(level = args.log_level or "INFO", format = '%(asctime)-15s %(levelname)s %(message)s')

    merge_editor_files(args.master_json, args.master_json, args.editor_jsons)
    exit(0)


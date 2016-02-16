#! /usr/bin/python
# -*- coding: utf-8 -*-

import argparse
import json
import os
import re
import codecs
from collections import OrderedDict
import logging
from logging import info, warning, debug, error

def collect_layoutloader_text(src_dir, target_filename="stringtable.txt"):
    if src_dir[-1] != '/':
        src_dir += '/'
    messages = OrderedDict()
    for root, dirs, files in os.walk(src_dir):
        for f in files:
            if target_filename != os.path.basename(f):
                continue
            base_dir = os.path.dirname(re.sub('^'+src_dir, '', os.path.join(root, f)))
            path = os.path.join(root, f)
            with codecs.open(path, 'r', 'utf-8') as f:
                lines = re.split('[\n\r]+', f.read())
            for l in lines:
                if not l.strip():
                    continue
                m = re.match('^([^\s]+)\s+([^\s]+)\s+"(.*)"$', l)
                if not m:
                    error("不正な %s のエントリがあります: %s" % (os.path.join(base_dir, target_filename), l))
                    raise Exception("invalid entry exists")
                key = os.path.dirname(base_dir)+'.'+m.group(1)
                messages[key] = m.group(3)
                debug("%s: %s" % (key, messages[key]))
            info("%s: %d" % (base_dir, len(lines)))
    return messages

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='generate json from layout loader text', epilog="""\
example:
    $ ./lltext2json.py --dest-json asset/master_derivatives/layoutloader_message.json asset/ui""")

    parser.add_argument('src_dirs', metavar='src.dir', nargs="*", help='input layout loader dirs contains *.txt to generate')
    parser.add_argument('--output-json', metavar='dest.json', help='output message list json')
    parser.add_argument('--merge-json', metavar='master_data.json', help = 'merge into master_data.json')
    parser.add_argument('--log-level', help = 'log level (WARNING|INFO|DEBUG). default: INFO')
    args = parser.parse_args()
    logging.basicConfig(level = args.log_level or "INFO", format = '%(asctime)-15s %(levelname)s %(message)s')

    info("input = %s" % ', '.join(args.src_dirs))
    info("output = %s" % args.output_json)

    messages = OrderedDict()
    for src_dir in args.src_dirs:
        messages.update(collect_layoutloader_text(src_dir))

    if args.output_json:
        with codecs.open(args.output_json, "w") as f:
            j = json.dumps(messages, ensure_ascii = False, indent = 4)
            f.write(j.encode("utf-8"))

    if args.merge_json:
        with codecs.open(args.merge_json, "r") as f:
            data = json.load(f, object_pairs_hook=OrderedDict)
        id = 0
        for d in data['message']:
            id = max(id, d['id'])
        for key, ja in messages.iteritems():
            id += 1
            data['message'].append({
                'id': id,
                'key': key,
                'ja': ja
            })
        with codecs.open(args.merge_json, "w") as f:
            j = json.dumps(data, ensure_ascii = False, indent = 4)
            f.write(j.encode("utf-8"))
    exit(0)

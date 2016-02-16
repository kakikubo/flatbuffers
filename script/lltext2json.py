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
    char_map = OrderedDict()
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
                font = m.group(2)
                message = m.group(3)
                messages[key] = message
                for char in list(message):
                    if not char_map.has_key(font):
                        char_map[font] = OrderedDict()
                    if not char_map[font].has_key(char):
                        char_map[font][char] = 0
                    char_map[font][char] += 1
                debug("%s %s: %s" % (key, font, messages[key]))
            info("%s: %d" % (base_dir, len(lines)))
    return (messages, char_map)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='generate json from layout loader text', epilog="""\
example:
    $ ./lltext2json.py --dest-json asset/master_derivatives/layoutloader_message.json asset/ui""")

    parser.add_argument('src_dirs', metavar='src.dir', nargs="*", help='input layout loader dirs contains *.txt to generate')
    parser.add_argument('--message-json', metavar='ll_message.json', help='output message list json')
    parser.add_argument('--char-map-json', metavar='ll_char_map.json', help='output char map json')
    parser.add_argument('--merge-json', metavar='master_data.json', help = 'merge into master_data.json')
    parser.add_argument('--log-level', help = 'log level (WARNING|INFO|DEBUG). default: INFO')
    args = parser.parse_args()
    logging.basicConfig(level = args.log_level or "INFO", format = '%(asctime)-15s %(levelname)s %(message)s')

    info("input = %s" % ', '.join(args.src_dirs))
    info("output message json = %s" % args.message_json)
    info("output char map json = %s" % args.char_map_json)

    messages = OrderedDict()
    char_map = OrderedDict()
    for src_dir in args.src_dirs:
        cur_messages, cur_char_map = collect_layoutloader_text(src_dir)
        messages.update(cur_messages)
        char_map.update(cur_char_map)

    if args.message_json:
        with codecs.open(args.message_json, "w") as f:
            j = json.dumps(messages, ensure_ascii = False, indent = 4)
            f.write(j.encode("utf-8"))

    if args.char_map_json:
        with codecs.open(args.char_map_json, "w") as f:
            j = json.dumps(char_map, ensure_ascii = False, indent = 4)
            f.write(j.encode("utf-8"))

    if args.merge_json:
        with codecs.open(args.merge_json, "r") as f:
            data = json.load(f, object_pairs_hook=OrderedDict)

        # merge into 'message'
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

        # merge into 'fontCharacter'
        id = 0
        for d in data['fontCharacter']:
            id = max(id, d['id'])
        keys = data['fontCharacter'][0].keys()
        for font, chars in char_map.iteritems():
            # FIXME temporary off
            #if not d.has_key(font):
            #    error(u"font '%s' は定義されていません: '%s'" % (font, "', '".join(chars)))
            #    raise Exception("undefined font name")
            for char in chars:
                id += 1
                d = OrderedDict()
                for k in keys:
                    d[k] = ""
                d['id'] = id
                d[font] = char
                data['fontCharacter'].append(d)

        with codecs.open(args.merge_json, "w") as f:
            j = json.dumps(data, ensure_ascii = False, indent = 4)
            f.write(j.encode("utf-8"))
    exit(0)

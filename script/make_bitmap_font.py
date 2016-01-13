#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
import codecs
import json
import logging
import argparse
import tempfile
from collections import OrderedDict
from subprocess import check_call
from logging import info, error, warning
from PIL import Image

sys.stdout = codecs.lookup(u'utf_8')[-1](sys.stdout)

global gdcl
gdcl = '/Applications/Glyph Designer 2.app/Contents/MacOS/Glyph Designer'

def load_char_map(input_json):
    char_map = OrderedDict()
    with open(input_json, 'r') as f:
        data = json.loads(f.read(), object_pairs_hook = OrderedDict)
    if not data.has_key('font'):
        return None
    for fc in data['font']:
        sheet = data[fc['sheet']]
        for d in sheet:
            font_name = fc['font']
            if not char_map.has_key(font_name):
                char_map[font_name] = OrderedDict()
            if not d.has_key(fc['field']):
                #raise Exception("field %s:%s not found: %s" % (fc['sheet'], fc['field'], d))
                continue
            for char in list(d[fc['field']]):
                if not char_map[font_name].has_key(char):
                    char_map[font_name][char] = 0
                char_map[font_name][char] += 1
    return char_map

def load_char_map_from_lua(lua_dirs):
    char_map = OrderedDict()
    for lua_dir in lua_dirs:
        for root, dirs, files in os.walk(os.path.dirname(lua_dir)):
            for f in files:
                path, ext = os.path.splitext(f)
                if ext != '.lua':
                    continue
                full_path = os.path.join(root, f)
                with codecs.open(full_path, 'r', 'utf-8') as f:
                    data = f.read()
                    for char in list(data):
                        for font_name in ['medium', 'bold']:
                            if not char_map.has_key(font_name):
                                char_map[font_name] = OrderedDict()
                            if not char_map[font_name].has_key(char):
                                char_map[font_name][char] = 0
                            char_map[font_name][char] += 1
    return char_map

def join_char_map(base_char_map, joining_char_map):
    for font_name, chars in joining_char_map.items():
        for char, count in chars.items():
            if not base_char_map.has_key(font_name):
                base_char_map[font_name] = OrderedDict()
            if not char_map[font_name].has_key(char):
                base_char_map[font_name][char] = 0
            base_char_map[font_name][char] += count
    return base_char_map

def generate_bitmap_font(char_map, gd_dir, font_dir):
    for font_name, chars in char_map.items():
        if not chars:
            continue
        char_list = chars.keys()
        char_list.sort()
        gd_prj    = gd_dir+'/'+font_name+'.GlyphProject'
        font_file = font_dir+'/'+font_name
        info("font: %s.fnt + %s.png by %s (%d characters)" % (font_name, font_name, gd_prj, len(char_list)))
        with tempfile.NamedTemporaryFile(prefix = 'json2font_'+font_name+'_', suffix = '.list', delete = False) as fp:
            fp.write(''.join(char_list).encode('utf-8'))
            fp.flush()
            cmdline = [gdcl, gd_prj, font_file, '-inf', fp.name]
            check_call(cmdline)

            image = Image.open(font_file+'.png', 'r')
            if image.size[0] > 2048 or image.size[1] > 2048:
                raise Exception("too large font file png: %s (%d x %d)" % (font_file+'.png', image.size[0], image.size[1]))

if __name__ == '__main__':
    logging.basicConfig(level = logging.INFO, format = '%(asctime)-15s %(levelname)s %(message)s')

    parser = argparse.ArgumentParser(description = 'master data xlsx to json converter')
    parser.add_argument('input_json', metavar = 'input.json',      help = 'input master data json')
    parser.add_argument('gd_dir',     metavar = 'input gd dir',    help = 'input glyph designer project dir')
    parser.add_argument('font_dir',   metavar = 'output font dir', help = 'output bitmap font dir')
    parser.add_argument('--lua-dir',  default = [], nargs='*', help = 'input lua script dir')
    args = parser.parse_args()

    if not os.path.exists(gdcl):
        warning("GlyphDesigner Command Line is not installed: %s" % gdcl)
        exit(1)

    # collect characters in target tables and columns
    info("input json: %s" % args.input_json)
    json_char_map = load_char_map(args.input_json)
    if not json_char_map:
        warning('"font" is not appeared')
        exit(1)

    # collect characters from lua script
    info("input lua dir: %s" % ", ".join(args.lua_dir))
    lua_char_map = load_char_map_from_lua(args.lua_dir)

    # write each font file
    info("output dir: %s" % args.font_dir)

    char_map = OrderedDict()
    char_map = join_char_map(char_map, json_char_map)
    char_map = join_char_map(char_map, lua_char_map)

    generate_bitmap_font(char_map, args.gd_dir, args.font_dir)

    exit(0)

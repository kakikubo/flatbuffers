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
            for char in d[fc['field']].split():
                if not char_map[font_name].has_key(char):
                    char_map[font_name][char] = 0
                char_map[font_name][char] += 1
    return char_map

def generate_bitmap_font(char_map, gd_dir, font_dir):
    for font_name, chars in char_map.items():
        if not chars:
            continue
        char_list = chars.keys()
        char_list.sort()
        gd_prj    = gd_dir+'/'+font_name+'.GlyphProject'
        font_file = font_dir+'/'+font_name
        info("font: %s.fnt + %s.png by %s (%d characters)" % (font_name, font_name, gd_prj, len(char_list)))
        with tempfile.NamedTemporaryFile(prefix = '', suffix = '', delete = False) as fp:
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
    args = parser.parse_args()

    if not os.path.exists(gdcl):
        warning("GlyphDesigner Command Line is not installed: %s" % gdcl)
        exit(0)

    # collect characters in target tables and columns
    info("input: %s" % args.input_json)
    char_map = load_char_map(args.input_json)
    if not char_map:
        warning('"font" is not appeared')
    else:
        # write each font file
        info("output dir: %s" % args.font_dir)
        generate_bitmap_font(char_map, args.gd_dir, args.font_dir)
    exit(0)

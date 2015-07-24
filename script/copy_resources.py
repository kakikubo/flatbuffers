#! /usr/bin/python
# -*- coding: utf-8 -*-

import argparse
import json
import os
import re
from collections import OrderedDict
import logging
from logging import info, warning, debug
import fnmatch
from shutil import rmtree, copy

def load_filter_list(filter_fnmatch_path):
    filter_list = []
    if filter_fnmatch_path:
        with open(filter_fnmatch_path, 'r') as f:
            lines = f.readlines()
        for i, l in enumerate(lines):
            l = re.sub('#.*', '', l)
            l = l.strip()
            if not l:
                continue
            filter_list.append(os.path.normpath(l))
    return filter_list

def copy_resources(src_dir, dest_dir, filter_list):
    for l in filter_list:
        info("copy %s" % l)
        src_dir = os.path.normpath(src_dir)
        if l[0] != '/':
            l = os.path.join(src_dir, l)
        for root, dirs, files in os.walk(os.path.dirname(l)):
            for f in files:
                sub_dir = re.sub(src_dir+'/', '', root)
                src = os.path.join(root, f)
                dest = os.path.join(dest_dir, sub_dir, f)
                if fnmatch.fnmatch(src, l):
                    if not os.path.isdir(os.path.dirname(dest)):
                        os.makedirs(os.path.dirname(dest))
                    debug("%s -> %s" % (src, dest))
                    copy(src, dest)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='copy asset files to Resources dir by bundled.list', epilog="""\
example:
    $ ./copy_resources.py asset/distribution/bundled.list asset/contents Resources""")

    parser.add_argument('src_dir', metavar='src.dir', help='asset dir to be copy source')
    parser.add_argument('dest_dir', metavar='dest.dir', help='dest Resource dir to copy')
    parser.add_argument('--filter', metavar='filter.list', required=True, help='asset filter list (fnmatch format)')
    parser.add_argument('--log-level', help = 'log level (WARNING|INFO|DEBUG). default: INFO')
    args = parser.parse_args()
    logging.basicConfig(level = args.log_level or "INFO", format = '%(asctime)-15s %(levelname)s %(message)s')

    filter_list = load_filter_list(args.filter)
    copy_resources(args.src_dir, args.dest_dir, filter_list)
    exit(0)

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
    rename_list = []
    cleanup_list = []
    ext_list = []
    if filter_fnmatch_path:
        with open(filter_fnmatch_path, 'r') as f:
            lines = f.readlines()
        for i, l in enumerate(lines):
            l = re.sub('#.*', '', l)
            l = l.strip()
            if not l:
                continue
            m1 = re.match('^\s*D\s+(.*)', l)
            m2 = re.match('^\s*EXT\s+(.*)', l)
            m3 = re.match('^\s*LOCATION\s+(.*)', l)
            m4 = re.match('^\s*CHARACTER\s+(.*)', l)
            m5 = re.match('^\s*UI\s+(.*)', l)
            m6 = re.match('^\s*INCLUDE\s+(.*)', l)
            m7 = re.match('^\s*([^\s]+)\s+([^\s]+)', l)
            if m1:
                cleanup_list.append(os.path.normpath(m1.group(1)))
            elif m2:
                ext_list = re.split('\s+', m2.group(1))
            elif m3 or m4 or m5:
                info("skip command: %s" % l)
            elif m6:
                include_path = m6.group(1)
                if include_path[0] != '/':
                    include_path = os.path.join(os.path.dirname(filter_fnmatch_path), include_path)
                in_filter_list, in_rename_list, in_cleanup_list, in_ext_list = load_filter_list(include_path)
                filter_list  += in_filter_list
                rename_list  += in_rename_list
                cleanup_list += in_cleanup_list
                ext_list     += in_ext_list
            elif m7:
                rename_list.append((os.path.normpath(m7.group(1)), os.path.normpath(m7.group(2))))
            else:
                filter_list.append(os.path.normpath(l))
    return (filter_list, rename_list, cleanup_list, ext_list)

def cleanup_resources(dest_dir, cleanup_list):
    for l in cleanup_list:
        info("cleanup %s" % l)
        if l[0] != '/':
            l = os.path.join(dest_dir, l)
        for root, dirs, files in os.walk(os.path.dirname(l)):
            for f in files + dirs:
                if f in ('.gitkeep', '.DS_Store'):
                    continue
                full_path = os.path.join(root, f)
                if fnmatch.fnmatch(full_path, l):
                    if os.path.isdir(full_path):
                        rmtree(full_path)
                    else:
                        os.remove(full_path)
    return True

def copy_resources(src_dir, dest_dir, filter_list, rename_list, ext_list):
    for l in filter_list:
        info("copy %s" % l)
        if l[0] != '/':
            l = os.path.join(src_dir, l)
        matched = False
        for root, dirs, files in os.walk(os.path.dirname(l)):
            if ext_list:
                file_map = OrderedDict()
                for f in files:
                    file_map[f] = True
                for f in file_map.keys():
                    name, ext = os.path.splitext(f)
                    if not ext[1:] in ext_list:
                        continue
                    for alter_ext in ext_list:
                        prior_file = name + '.' + alter_ext
                        if f == prior_file:
                            break
                        elif prior_file in file_map:
                            del file_map[f]
                files = file_map.keys()

            for f in files:
                sub_dir = re.sub(src_dir, '', root)
                if sub_dir and sub_dir[0] == '/': 
                    sub_dir = sub_dir[1:]
                src = os.path.join(root, f)
                dest = os.path.join(dest_dir, sub_dir, f)
                if fnmatch.fnmatch(src, l):
                    if not os.path.isdir(os.path.dirname(dest)):
                        os.makedirs(os.path.dirname(dest))
                    debug("%s -> %s" % (src, dest))
                    copy(src, dest)
                    matched = True
        if not matched:
            raise Exception("filter target file is not found: '%s'" % l)

    for l in rename_list:
        info("copy with rename: '%s' -> '%s'" % (l[0], l[1]))
        src  = os.path.join(src_dir,  l[0]) if l[0][0] != '/' else l[0]
        dest = os.path.join(dest_dir, l[1]) if l[1][0] != '/' else l[1]
        if not os.path.isdir(os.path.dirname(dest)):
            os.makedirs(os.path.dirname(dest))
        debug("%s -> %s" % (src, dest))
        copy(src, dest)
      
    return True

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='copy asset files to Resources dir by bundled.list', epilog="""\
example:
    $ ./copy_resources.py --filter asset/distribution/bundled.list asset/contents Resources""")

    parser.add_argument('src_dir', metavar='src.dir', help='asset dir to be copy source')
    parser.add_argument('dest_dir', metavar='dest.dir', help='dest Resource dir to copy')
    parser.add_argument('--filter', metavar='filter.list', required=True, help='asset filter list (fnmatch format)')
    parser.add_argument('--log-level', help = 'log level (WARNING|INFO|DEBUG). default: INFO')
    args = parser.parse_args()
    logging.basicConfig(level = args.log_level or "INFO", format = '%(asctime)-15s %(levelname)s %(message)s')

    src_dir  = os.path.normpath(args.src_dir)
    dest_dir = os.path.normpath(args.dest_dir)
    filter_list, rename_list, cleanup_list, ext_list = load_filter_list(args.filter)
    cleanup_resources(dest_dir, cleanup_list)
    copy_resources(src_dir, dest_dir, filter_list, rename_list, ext_list)
    exit(0)

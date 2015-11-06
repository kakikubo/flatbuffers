#! /usr/bin/python
# -*- coding: utf-8 -*-

import argparse
import os
import re
from collections import OrderedDict
import logging
from logging import info, warning, debug
from glob import glob
from subprocess import check_call
from shutil import move, rmtree, copy2

def pack_textures(src_dir, dest_dir, work_dir=None):
    work_dir = work_dir or dest_dir
    cmdline_base = [
        'TexturePacker', 
        '--format', 'cocos2d', 
        '--texture-format', 'png', 
        '--replace', '@@SEPARATOR@@=/',
        #'--max-size', '2048', 
        '--max-size', '1024', 
        '--force-squared', 
        '--force-word-aligned', 
        '--pack-mode', 'Best', 
        '--padding', '8',
        '--algorithm', 'MaxRects', 
        '--multipack',
    ]
    for top_dir in glob(src_dir+'/*'):
        if not os.path.isdir(top_dir):
            continue
        for root, dirs, files in os.walk(top_dir):
            for f in files:
                if not re.search('\.png$', f):
                    continue
                if re.search('textures\.[0-9]+\.png', f):
                    continue
                # include sub dir path to texture name 
                base_dir = re.sub('^'+src_dir+'/', '', root)
                fname = re.sub('/', '@@SEPARATOR@@', os.path.join(base_dir, f))
                dest = os.path.join(work_dir, os.path.basename(top_dir), fname)
                if not os.path.exists(os.path.dirname(dest)):
                    os.makedirs(os.path.dirname(dest))
                copy2(os.path.join(root, f), dest)

    for top_dir in glob(work_dir+'/*'):
        if not os.path.isdir(top_dir):
            continue
        targets = []
        for root, dirs, files in os.walk(top_dir):
            for f in files:
                targets.append(os.path.join(root, f))
        if targets:
            dir = os.path.join(dest_dir, re.sub('^'+work_dir+'/', '', root))
            if not os.path.isdir(dir):
                os.makedirs(dir)
            cmdline = list(cmdline_base)
            cmdline.extend(['--sheet', os.path.join(dir, 'textures.{n}.png')])
            cmdline.extend(['--data',  os.path.join(dir, 'textures.{n}.plist')])
            cmdline.extend(targets)
            debug(' '.join(cmdline))
            check_call(cmdline)
    return True

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='pack ui textures (PNG) by TexturePacker CLI', epilog="""\
example:
    $ ./make_ui_atlas.py asset/ui asset/texturepacker/ui""")

    parser.add_argument('src_dir', metavar='src.dir', help='asset dir to be packing source')
    parser.add_argument('dest_dir', metavar='dest.dir', help='dest Resource dir to copy')
    parser.add_argument('--work-dir', help = 'working directory. default: dest_dir')
    parser.add_argument('--log-level', help = 'log level (WARNING|INFO|DEBUG). default: INFO')
    args = parser.parse_args()
    logging.basicConfig(level = args.log_level or "INFO", format = '%(asctime)-15s %(levelname)s %(message)s')

    src_dir  = os.path.normpath(args.src_dir)
    dest_dir = os.path.normpath(args.dest_dir)
    pack_textures(src_dir, dest_dir, args.work_dir)
    exit(0)


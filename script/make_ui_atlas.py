#! /usr/bin/python
# -*- coding: utf-8 -*-

import argparse
import os
import re
import codecs
from collections import OrderedDict
import logging
from logging import info, warning, debug
from glob import glob
from subprocess import check_call
from shutil import move, rmtree, copy2

def pack_textures(src_dir, dest_dir, work_dir=None, verify_filename=False):
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
        '--padding', '4',
        '--size-constraints', 'POT',
        '--trim-mode', 'Trim',
        '--algorithm', 'MaxRects',
        '--multipack',
    ]
    for top_dir in glob(src_dir+'/*'):
        if not os.path.isdir(top_dir):
            continue
        for root, dirs, files in os.walk(top_dir):
            for d in dirs:
                if verify_filename and not re.match('^[a-z0-9_./]+$', d):
                    raise Exception("不正なフォルダ名です: %s" % os.path.join(root, d))
            for f in files:
                if not re.search('\.png$', f):
                    continue
                if re.search('textures\.[0-9]+\.png', f):
                    continue
                if verify_filename and not re.match('^[a-z0-9_./]+$', f):
                    raise Exception("不正なファイル名です: %s" % os.path.join(root, f))
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

def copy_json(src_dir, dest_dir):
    for top_dir in glob(src_dir+'/*'):
        for root, dirs, files in os.walk(top_dir):
            for f in files:
                name, ext = os.path.splitext(f)
                if ext != '.json':
                    continue
                dest = os.path.join(dest_dir, os.path.basename(top_dir), f)
                info("setup %s/%s" % (os.path.basename(top_dir), f))
                copy2(os.path.join(root, f), dest)
    return True

if __name__ == '__main__':
    sys.stdout = codecs.lookup('utf_8')[-1](sys.stdout)
    sys.stderr = codecs.lookup('utf_8')[-1](sys.stderr)
    parser = argparse.ArgumentParser(description='pack ui textures (PNG) by TexturePacker CLI', epilog="""\
example:
    $ ./make_ui_atlas.py asset/ui asset/texturepacker/ui""")

    parser.add_argument('src_dir', metavar='src.dir', help='asset dir to be packing source')
    parser.add_argument('dest_dir', metavar='dest.dir', help='dest Resource dir to copy')
    parser.add_argument('--work-dir', help = 'working directory. default: dest_dir')
    parser.add_argument('--verify-filename', default = False, action = 'store_true', help = 'verify filename is composed only by lower case')
    parser.add_argument('--log-level', help = 'log level (WARNING|INFO|DEBUG). default: INFO')
    args = parser.parse_args()
    logging.basicConfig(level = args.log_level or "INFO", format = '%(asctime)-15s %(levelname)s %(message)s')

    if not os.path.exists('/usr/local/bin/TexturePacker'):
        warning("TexturePacker is not installed: /usr/local/bin/TexturePacker")
        exit(0)

    src_dir  = os.path.normpath(args.src_dir)
    dest_dir = os.path.normpath(args.dest_dir)
    info("input dir = %s" % src_dir)
    info("output dir = %s" % dest_dir)
    info("work dir = %s" % args.work_dir)
    info("verify filename = %s" % args.verify_filename)
    pack_textures(src_dir, dest_dir, args.work_dir, args.verify_filename)
    copy_json(src_dir, dest_dir)
    exit(0)

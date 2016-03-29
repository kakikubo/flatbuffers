#! /usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import re
import codecs
import subprocess
import shutil
import argparse
import logging
from multiprocessing import Process
from logging import info, warning, debug

class MakeAreaAtlas():
    def __init__(self, src_dir, dest_dir, work_dir = None):
        self.src_dir  = src_dir
        self.dest_dir = dest_dir
        self.work_dir = work_dir or dest_dir + "/_temp"

    def verify_filename(self, dir):
        for root, dirs, files in os.walk(dir):
            for f in dirs + files:
                if not re.match('^[a-z0-9_./]+$', f):
                    raise Exception("invalid filename is detected: %s" % os.path.join(root, f))
        return True

    def get_file_count(self, dir):
        if not os.path.isdir(dir): return 0
        i=0
        for root, dirs, files in os.walk(dir):
            i+=len(files)
        return i

    def make_area_atlas_by_category(self, top_dir, category_dir):
          # フォルダ階層も名前に含みたいので作業フォルダにコピーしてからコンバートする
          category_src_dir = os.path.join(self.src_dir, top_dir, category_dir)
          category_work_dir = os.path.join(self.work_dir, top_dir, category_dir)
          if not os.path.isdir(category_src_dir):
              return False
          if os.path.exists(category_work_dir):
              shutil.rmtree(category_work_dir)
          if not os.path.exists(os.path.dirname(category_work_dir)):
              os.makedirs(os.path.dirname(category_work_dir))
          shutil.copytree(category_src_dir, category_work_dir)

          base = "{0}/{1}/{1}_{2}".format(self.dest_dir, top_dir, category_dir)

          plistFile = base + "_{n}.plist"
          imageFile = base + "_{n}.png"
          textureType = "png"
          textureFormat = "RGBA8888"
          pvrQuality = "very-low"
          scale = "1.0"
          borderPadding = "2"
          extrude = "4"

          fnum = self.get_file_count(category_work_dir)
          print "{0} : textures num[{1}]".format(category_src_dir, fnum)
          if fnum == 0:
              return False
          if "single" in category_dir:
              borderPadding = "0"
              extrude = "0"

          subprocess.check_call(["TexturePacker",
              "--sheet", imageFile,
              "--texture-format", textureType,
              "--format", "cocos2d",
              "--data", plistFile,
              "--prepend-folder-name",
              "--replace", "^="+top_dir+'/',
              "--algorithm", "MaxRects",
              "--maxrects-heuristics", "Best",
              "--basic-sort-by", "Best",
              "--basic-order", "Ascending",
              "--max-size", "2048",
              "--size-constraints", "POT",
              "--force-squared",
              "--force-word-aligned",
              "--pack-mode", "Best",
              "--multipack",
              "--common-divisor-x", "4",
              "--common-divisor-y", "4",
              "--shape-padding", "2",
              "--border-padding", borderPadding,
              "--enable-rotation",
              "--trim-mode", "None",
              # "--disable-clean-transparency",
              "--opt", textureFormat,
              "--pvr-quality", pvrQuality,
              # "--premultiply-alpha",
              "--png-opt-level", "0",
              "--extrude", extrude,
              "--scale", scale,
              "--scale-mode", "Smooth",
               category_work_dir])

          #現在png側をコンバートした時のplistを使っているので特に要らないファイル。が、上書きしちゃうと再ビルドの時に全部ビルドが走ってしまうらしい。。。
          plistFile = base + "_{n}.pvr.plist"
          
          #imageFile = base + "_{n}.pvr.ccz"
          imageFile = base + "_{n}.pvr"
          #textureType = "pvr3ccz"
          textureType = "pvr3"
          textureFormat = "PVRTC4"
          pvrQuality = "very-low"
          #pvrQuality = "best"
          scale = "1.0"

          subprocess.check_call(["TexturePacker",
              "--sheet", imageFile,
              "--texture-format", textureType,
              "--format", "cocos2d",
              "--data", plistFile,
              "--prepend-folder-name",
              "--replace", "^="+top_dir+'/',
              "--algorithm", "MaxRects",
              "--maxrects-heuristics", "Best",
              "--basic-sort-by", "Best",
              "--basic-order", "Ascending",
              "--max-size", "2048",
              "--size-constraints", "POT",
              "--force-squared",
              "--force-word-aligned",
              "--pack-mode", "Best",
              "--multipack",
              "--common-divisor-x", "4",
              "--common-divisor-y", "4",
              "--shape-padding", "2",
              "--border-padding", borderPadding,
              "--enable-rotation",
              "--trim-mode", "None",
              # "--disable-clean-transparency",
              "--opt", textureFormat,
              "--pvr-quality", pvrQuality,
              # "--premultiply-alpha",
              "--png-opt-level", "0",
              "--extrude", extrude,
              "--scale", scale,
              "--scale-mode", "Smooth",
               category_work_dir])

    def make_area_atlas(self, top_dir):
        category_top_dir = os.path.join(self.src_dir, top_dir)
        if not os.path.isdir(category_top_dir):
            return True

        category_dirs = os.listdir(category_top_dir)
        for category_dir in category_dirs:
            self.make_area_atlas_by_category(top_dir, category_dir)

        return True

    def make_area_atlas_all(self):
        top_dirs = os.listdir(self.src_dir)
        processes = []
        for top_dir in top_dirs:
            processes.append(Process(target = self.make_area_atlas, args=(top_dir, )))
        for p in processes:
            p.start()
        for p in processes:
            p.join()
        for p in processes:
            if p.exitcode != 0:
                raise Exception("process '%s' exited by '%d'" % (p, p.exitcode))

# ---
# main function
#
if __name__ == '__main__':
    sys.stdout = codecs.lookup('utf_8')[-1](sys.stdout)
    parser = argparse.ArgumentParser(description='pack area textures (PNG) by TexturePacker CLI', epilog="""\
example:
    $ ./make_area_atlas.py asset/area asset/texturepacker/areaAtlas""")

    parser.add_argument('src_dir', metavar='src.dir', help='asset dir to be packing source')
    parser.add_argument('dest_dir', metavar='dest.dir', help='dest Resource dir to copy')
    parser.add_argument('--work-dir', help = 'working directory. default: dest_dir')
    parser.add_argument('--verify-filename', default = False, action = 'store_true', help = 'verify filename is composed only by lower case')
    parser.add_argument('--log-level', help = 'log level (WARNING|INFO|DEBUG). default: INFO')
    args = parser.parse_args()
    logging.basicConfig(level = args.log_level or "INFO", format = '%(asctime)-15s %(process)d %(levelname)s %(message)s')

    if not os.path.exists('/usr/local/bin/TexturePacker'):
        warning("TexturePacker is not installed: /usr/local/bin/TexturePacker")
        exit(0)

    src_dir  = os.path.normpath(args.src_dir)
    dest_dir = os.path.normpath(args.dest_dir)
    info("input dir = %s" % src_dir)
    info("output dir = %s" % dest_dir)
    info("work dir = %s" % args.work_dir)
    info("verify filename = %s" % args.verify_filename)

    make = MakeAreaAtlas(args.src_dir, args.dest_dir, args.work_dir)
    if args.verify_filename:
        make.verify_filename(src_dir)
    make.make_area_atlas_all()


#! /usr/bin/env python
# -*- coding: utf-8 -*-

import os.path
import shutil
import sys
import codecs
import json
import argparse
from collections import OrderedDict
import xlrd 
from shutil import copy2
import logging
from logging import info, warning, debug

def make_weapon_atlas(master_excel, sheet_name, start_row, start_col, dest_dir, complete_png):
    book = xlrd.open_workbook(master_excel)
    sheet = book.sheet_by_name(sheet_name)

    real_start_col = -1
    for col in range(sheet.ncols):
        if sheet.cell_value(0, col) == start_col:
            real_start_col = col
            break
    if real_start_col < 0:
        raise Exception("can not find start_col %s" % start_col)

    for row in range(sheet.nrows):
        if row < int(start_row):
            continue
        model_id = int(sheet.cell_value(row, 0))
        dest_atlas = os.path.join(dest_dir, str(model_id)+".atlas")

        x = sheet.cell_value(row, real_start_col)
        y = sheet.cell_value(row, real_start_col+1)
        w = sheet.cell_value(row, real_start_col+2)
        h = sheet.cell_value(row, real_start_col+3)
        s = 1.0 / sheet.cell_value(row, real_start_col+4)

        print "{0}:{1}:{2}:{3}:{4}".format(x,y,w,h,s)

        with open(dest_atlas, 'w') as f:
            base = "{0}.png\nformat: RGBA8888\nfilter: Linear,Linear\nrepeat: none\n{1}\n  rotate: false\n  xy: 0,0\n  size: {2},{3}\n  orig: {4},{5}\n  offset: {6},{7}\n  index: -1\n"
            size_x = w
            size_y = h
            orig_x = w/s
            orig_y = h/s
            center_x = w/2.0
            center_y = h/2.0
            offset_x = center_x - x - orig_x/s
            offset_y = y - center_y - orig_y/s
            f.write(base.format(model_id, model_id, size_x, size_y, orig_x, orig_y, offset_x, offset_y))

        png_path = os.path.join(dest_dir, str(model_id)+'.png')
        if not os.path.exists(png_path):
            copy2(complete_png, png_path)

# ---
# main function
#
if __name__ == '__main__':
    sys.stdout = codecs.lookup('utf_8')[-1](sys.stdout)
    parser = argparse.ArgumentParser(description='generate weapon textures (PNG+Atlas)', epilog="""\
example:
    $ ./make_weapon_atlas.py master/weaponPosition.xlsx weaponPosition 3 positionX contents/files/weapon""")
    parser.add_argument('master_xlsx', metavar='master.xlsx', help='master data excel file')
    parser.add_argument('sheet_name', help='master data sheet name')
    parser.add_argument('start_row', help='start row in target sheet')
    parser.add_argument('start_col', help='start column in target sheet')
    parser.add_argument('dest_dir', help='atlases output dir')
    parser.add_argument('--complete-png', help = 'complete png file if it does not exist')
    parser.add_argument('--log-level', help = 'log level (WARNING|INFO|DEBUG). default: INFO')
    args = parser.parse_args()
    logging.basicConfig(level = args.log_level or "INFO", format = '%(asctime)-15s %(levelname)s %(message)s')

    make_weapon_atlas(args.master_xlsx, args.sheet_name, args.start_row, args.start_col, args.dest_dir, args.complete_png)

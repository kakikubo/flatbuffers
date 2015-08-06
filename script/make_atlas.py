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

def makeAtlas(masterExcel, sheetName, paramStartRow, paramStartField, dstFolderPath):
    iParamStartRow = int(paramStartRow)
    iParamStartCol = -1
    book = xlrd.open_workbook(masterExcel)
    sheet = book.sheet_by_name(sheetName)

    for col in range(sheet.ncols):
        if sheet.cell_value(0, col) == paramStartField:
            iParamStartCol = col
            break

    if iParamStartCol >= 0:
        for row in range(sheet.nrows):
            if (row >= iParamStartRow):
                modelId = int(sheet.cell_value(row, 0))
                strModelId = str(modelId)
                dstAtlas = dstFolderPath + "/" + strModelId + ".atlas"

                x = sheet.cell_value(row, iParamStartCol)
                y = sheet.cell_value(row, iParamStartCol+1)
                w = sheet.cell_value(row, iParamStartCol+2)
                h = sheet.cell_value(row, iParamStartCol+3)
                s = 1.0 / sheet.cell_value(row, iParamStartCol+4)

                print "{0}:{1}:{2}:{3}:{4}".format(x,y,w,h,s)

                with open(dstAtlas, 'w') as f:
                    base = "{0}.png\nformat: RGBA8888\nfilter: Linear,Linear\nrepeat: none\n{1}\n  rotate: false\n  xy: 0,0\n  size: {2},{3}\n  orig: {4},{5}\n  offset: {6},{7}\n  index: -1\n"
                    size_x = w
                    size_y = h
                    orig_x = w/s
                    orig_y = h/s
                    center_x = w/2.0
                    center_y = h/2.0
                    offset_x = center_x - x - orig_x/s
                    offset_y = y - center_y - orig_y/s
                    f.write(base.format(modelId, modelId, size_x, size_y, orig_x, orig_y, offset_x, offset_y))
    else:
        print "can not find startCol {0}".format(paramStartField)

# ---
# main function
#
if __name__ == '__main__':
    sys.stdout = codecs.lookup('utf_8')[-1](sys.stdout)
    argv = sys.argv
    argc = len(argv)
    if argc == 6:
        makeAtlas(argv[1], argv[2], argv[3], argv[4], argv[5])
    else:
        # python /Users/motoshi.abe/my/dev/git/wfs/kms/client/tool/script/make_atlas.py /Users/motoshi.abe/Box\ Sync/kms_master_asset/master/weapon.xlsx weaopn /Users/motoshi.abe/Box\ Sync/kms_master_asset/contents/files/spine/weapon 
        print "python make_atlas.py {excel file name} {sheet name} {id start row} {param start col} {dstfolderpath}"






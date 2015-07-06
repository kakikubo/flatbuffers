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

def makeAtlas(masterExcel, sheetName, paramStartRow, srcFolderPath, dstFolderPath):
    iParamStartRow = int(paramStartRow)
    book = xlrd.open_workbook(masterExcel)
    sheet = book.sheet_by_name(sheetName)

    for row in range(sheet.nrows):
        if (row >= iParamStartRow):
            modelId = int(sheet.cell_value(row, 0))
            strModelId = str(modelId)
            srcJson = srcFolderPath + "/" + strModelId + ".json"
            srcPng = srcFolderPath + "/" + strModelId + ".png"
            dstAtlas = dstFolderPath + "/" + strModelId + ".atlas"

            x = 0
            y = 0
            w = 0
            h = 0
            s = 2.0 # 今スケール値を貰ってないので貰うようにする

            with open(srcJson, 'r') as f:
                jsonData = json.loads(f.read(), object_pairs_hook=OrderedDict)
                if jsonData.has_key(strModelId):
                    model = jsonData[strModelId]
                    if model.has_key("x"):
                        x = model["x"]
                    else:
                        print "can not find 'x' named [{0}] dictionary.".format(strModelId)

                    if model.has_key("y"):
                        y = model["y"]
                    else:
                        print "can not find 'y' named [{0}] dictionary.".format(strModelId)

                    if model.has_key("width"):
                        w = model["width"]
                    else:
                        print "can not find 'width' named [{0}] dictionary.".format(strModelId)

                    if model.has_key("height"):
                        h = model["height"]
                    else:
                        print "can not find 'height' named [{0}] dictionary.".format(strModelId)
            
                    if model.has_key("scale"):
                        s = 1.0 / model["scale"]
                    else:
                        print "can not find 'scale' named [{0}] dictionary.".format(strModelId)

                else:
                    print "can not find named [{0}] dictionary.".format(strModelId)

            with open(dstAtlas, 'w') as f:
                base = "{0}.png\nformat: RGBA8888\nfilter: Linear,Linear\nrepeat: none\n{1}\n  rotate: false\n  xy: 0,0\n  size: {2},{3}\n  orig: {4},{5}\n  offset: {6},{7}\n  index: -1\n"
                size_x = w
                size_y = h
                orig_x = w/s
                orig_y = h/s
                center_x = w/2
                center_y = h/2
                offset_x = center_x - x - orig_x/s
                offset_y = y - center_y - orig_y/s
                f.write(base.format(modelId, modelId, size_x, size_y, orig_x, orig_y, offset_x, offset_y))

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
        print "python make_atlas.py {excel file name} {sheet name} {id start row} {srcfolderpath} {dstfolderpath}"






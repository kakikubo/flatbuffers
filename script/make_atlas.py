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

def makeAtlas(masterExcel, sheetName, paramStartRow, folderPath):
    iParamStartRow = int(paramStartRow)
    book = xlrd.open_workbook(masterExcel)
    sheet = book.sheet_by_name(sheetName)

    for row in range(sheet.nrows):
        if (row >= iParamStartRow):
            modelId = int(sheet.cell_value(row, 0))
            strModelId = str(modelId)
            srcJson = folderPath + "/" + strModelId + ".json"
            srcPng = folderPath + "/" + strModelId + ".png"
            dstAtlas = folderPath + "/" + strModelId + ".atlas"

            x = 0
            y = 0
            width = 0
            height = 0

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
                        width = model["width"]
                    else:
                        print "can not find 'width' named [{0}] dictionary.".format(strModelId)

                    if model.has_key("height"):
                        height = model["height"]
                    else:
                        print "can not find 'height' named [{0}] dictionary.".format(strModelId)
                else:
                    print "can not find named [{0}] dictionary.".format(strModelId)

            with open(dstAtlas, 'w') as f:
                base = "{0}.png\nsize: {1},{2}\nformat: RGBA8888\nfilter: Linear,Linear\nrepeat: none\n{3}\n  rotate: false\n  xy: 0,0\n  size: {4},{5}\n  orig: {6},{7}\n  offset: {8},{9}\n  index: -1\n"
                f.write(base.format(modelId, width, height, modelId, width, height, width, height, x, -y))

# ---
# main function
#
if __name__ == '__main__':
    sys.stdout = codecs.lookup('utf_8')[-1](sys.stdout)
    argv = sys.argv
    argc = len(argv)
    if argc == 5:
        makeAtlas(argv[1], argv[2], argv[3], argv[4])
    else:
        # python /Users/motoshi.abe/my/dev/git/wfs/kms/client/tool/script/make_atlas.py /Users/motoshi.abe/Box\ Sync/kms_master_asset/master/weapon.xlsx weaopn /Users/motoshi.abe/Box\ Sync/kms_master_asset/contents/files/spine/weapon 
        print "python make_atlas.py {excel file name} {sheet name} {id start row} {folderpath}"






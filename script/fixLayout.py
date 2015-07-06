#! /usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import codecs
import json
import re
import datetime
import argparse
import logging
import os
import shutil
from logging import info, warning, error
from collections import OrderedDict

def fixLayout11():
    json_file = "./kms_tomohiko.furumoto_asset/editor/areaInfo/areaInfo_519001011.json"
    with open(json_file, 'r') as f:
        master = json.loads(f.read(), object_pairs_hook=OrderedDict)
        offsetX = 0
        offsetY = 0
        num = 0
        for item in master["areaInfo_item"]["ground"]:           
            if item["image"] != "area/dogma/ground/dogma_ground.png":
                continue
            offsetX += item["x"]%450
            offsetY += item["y"]%350
            num += 1
        offsetX /= num
        offsetY /= num
        print "offset " + str(offsetX) + "," + str(offsetY)
        for item in master["areaInfo_item"]["ground"]:           
            if item["image"] != "area/dogma/ground/dogma_ground.png":
                continue
            item["x"] = item["x"]/450 * 450 + offsetX
            item["y"] = item["y"]/350 * 350 + offsetY

    with open(json_file + ".converted", 'w') as f:
        j = json.dumps(master, ensure_ascii = False, indent = 4)
        f.write(j.encode("utf-8"))

def fixLayout10():
    json_file = "./kms_tomohiko.furumoto_asset/editor/areaInfo/areaInfo_519001010.json"
    with open(json_file, 'r') as f:
        master = json.loads(f.read(), object_pairs_hook=OrderedDict)
        offsetX = 0
        offsetY = 0
        num = 0
        for item in master["areaInfo_item"]["ground"]:           
            if item["image"] != "area/dogchana/ground/dogchana_ground.png":
                continue
            offsetX += item["x"]%450
            offsetY += item["y"]%350
            num += 1
        offsetX /= num
        offsetY /= num
        print "offset " + str(offsetX) + "," + str(offsetY)
        for item in master["areaInfo_item"]["ground"]:           
            if item["image"] != "area/dogchana/ground/dogchana_ground.png":
                continue
            item["x"] = item["x"]/450 * 450 + offsetX
            item["y"] = item["y"]/350 * 350 + offsetY

    with open(json_file + ".converted", 'w') as f:
        j = json.dumps(master, ensure_ascii = False, indent = 4)
        f.write(j.encode("utf-8"))

def fixLayout09():
    json_file = "./kms_tomohiko.furumoto_asset/editor/areaInfo/areaInfo_519001009.json"
    with open(json_file, 'r') as f:
        master = json.loads(f.read(), object_pairs_hook=OrderedDict)
        offsetGroundX = 0
        offsetGroundY = 0
        numGround = 0
        offsetX = 0
        offsetY0 = 0
        offsetY1 = 0
        offsetY2 = 0
        num0 = 0
        num1 = 0
        num2 = 0
        for item in master["areaInfo_item"]["ground"]:           
            if item["image"] != "area/zarubo/ground/zarubo_ground.png":
                continue
            offsetGroundX += item["x"]%450
            offsetGroundY += item["y"]%350
            numGround += 1

        offsetGroundX /= numGround
        offsetGroundY /= numGround

        for item in master["areaInfo_item"]["ground"]:           
            if item["image"] != "area/zarubo/ground/zarubo_ground.png":
                continue
            item["x"] = item["x"]/450 * 450 + offsetGroundX
            item["y"] = item["y"]/350 * 350 + offsetGroundY

        for item in master["areaInfo_item"]["ground"]:           
            if item["image"] != "area/zarubo/ground/zarubo_roadx.png":
                continue
            offsetX += item["x"]%450
            y = item["y"]
            if y < 2500:
                offsetY0 += item["y"]%350
                num0+=1
                print(str(item["y"]) + " " + str(item["y"]%350) + " " + str(offsetY0/num0))
            elif y < 3000:
                offsetY1 += item["y"]%350
                num1+=1
            else:
                offsetY2 += item["y"]%350
                num2+=1

        offsetX /= num0 + num1 + num2
        offsetY0 /= num0
        offsetY1 /= num1
        offsetY2 /= num2
        print "offset " + str(offsetY0) + "," +  str(offsetY1) + "," + str(offsetY2)

        for item in master["areaInfo_item"]["ground"]:           
            if item["image"] != "area/zarubo/ground/zarubo_roadx.png":
                continue
            item["x"] = item["x"]/450 * 450 + offsetX
            y = item["y"]
            if y < 2500:
                before = item["y"]
                item["y"] = item["y"]/350 * 350 + offsetY0
                print(str(before) + "->" + str(item["y"]))
            elif y < 3000:
                item["y"] = item["y"]/350 * 350 + offsetY1
            else:
                item["y"] = item["y"]/350 * 350 + offsetY2

    master["areaInfo_item"]["areaId"] = 519001909
    with open("./kms_tomohiko.furumoto_asset/editor/areaInfo/areaInfo_519001909.json", 'w') as f:
        j = json.dumps(master, ensure_ascii = False, indent = 4)
        f.write(j.encode("utf-8"))

# ---
# main function
#
if __name__ == '__main__':
    fixLayout09()
    #fixLayout11()
    #fixLayout10()
    exit(0)

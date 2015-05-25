#! /usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import codecs
import json
import re
import datetime
import argparse
import logging
from logging import info, warning, error
from collections import OrderedDict

def ll2newLayout(master_asset_root, dst_filename):
    ground = []
    wall = []
    with open(master_asset_root + "/master_derivatives/master_data.json", 'r') as f:
        master = json.loads(f.read(), object_pairs_hook=OrderedDict)
        for item in master["layoutDeprecated"]:
            #print(item["name"] + "\t" + item["type"] + "\t" + "@(" + str(item["x"]) + "," + str(item["z"]) + ")")
            name = item["name"]
            ox = item["x"]
            oy = item["z"]
            layout_type = item["type"]
            with open(master_asset_root + "/contents/files/mapTest/"+name+".textures/"+name+".json.txt", 'r') as ff:
                layout = json.loads(ff.read(), object_pairs_hook=OrderedDict)
                for llitem in layout["root"]["childs"]:
                    if llitem["class"] == "Sprite":
                        if llitem.pop("childs"):
                            print "error: not empty children"
                        i = {}
                        i["image"] = llitem["image"]
                        i["width"] = llitem["size"]["width"]
                        i["height"] = llitem["size"]["height"]
                        i["x"] = llitem["position"]["x"] + ox;
                        i["y"] = llitem["position"]["y"] + oy;
                        i["layer"] = llitem["z"]

                        if layout_type == "ground":
                            ground.append(i)
                        if layout_type == "wall" or layout_type == "bg":
                            wall.append(i)
    result = {}
    result["openWorld"] = {}
    result["openWorld"]["ground"] = ground
    result["openWorld"]["wall"] = wall
    with open(dst_filename, 'w') as f:
        j = json.dumps(result, ensure_ascii = False, indent = 4)
        f.write(j.encode("utf-8"))
# ---
# main function
#
if __name__ == '__main__':
    master_asset_root = "./kms_master_asset"
    ll2newLayout(master_asset_root, "./openWorld.json")
    exit(0)

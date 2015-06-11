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

def ll2newLayout(master_asset_root, dst_asset_root):
    result = {}

    with open(master_asset_root + "/master_derivatives/master_data.json", 'r') as f:
        master = json.loads(f.read(), object_pairs_hook=OrderedDict)
        for item in master["layoutDeprecated"]:
            #print(item["name"] + "\t" + item["type"] + "\t" + "@(" + str(item["x"]) + "," + str(item["z"]) + ")")
            name = item["name"]
            is_ground = item["type"] == "ground"
            is_bg = item["type"] == "bg"
            is_wall = item["type"] == "wall"
            area_id = str(item["mapID"])
            if not area_id in result:
                result[area_id] = {"areaId":item["mapID"], "ground":[], "wall":[], "bg":[]}

            origin_x = item["x"]
            origin_y = item["y"]
            origin_z = item["z"]
    
            with open(master_asset_root + "/contents/files/mapTest/"+name+".textures/"+name+".json.txt", 'r') as ff:
                layout = json.loads(ff.read(), object_pairs_hook=OrderedDict)
                for llitem in layout["root"]["childs"]:
                    if llitem["class"] == "Sprite":
                        if llitem.pop("childs"):
                            print "error: not empty children in sprite"
                        i = {}
                        i["image"] = llitem["image"].replace("common_","")
                        i["width"] = llitem["size"]["width"]
                        i["height"] = llitem["size"]["height"]
                        if is_ground:
                            i["x"] = llitem["position"]["x"] + origin_x
                            i["y"] = llitem["position"]["y"] + origin_y
                            i["layer"] = llitem["z"]
                        else:
                            i["x"] = llitem["position"]["x"] + origin_x
                            i["y"] = origin_y
                            i["z"] = origin_z + llitem["z"]
                            i["offsetX"] = 0
                            i["offsetY"] = llitem["position"]["y"]
                        if is_ground:
                            result[area_id]["ground"].append(i)
                        elif is_wall:
                            result[area_id]["wall"].append(i)
                        elif is_bg:
                            result[area_id]["bg"].append(i)
    dst_json_dir = dst_asset_root + "/editor/areaInfo"
    if not os.path.exists(dst_json_dir):
        os.makedirs(dst_json_dir)

    dst_image_dir = dst_asset_root + "/contents/files/area/test1"
    src_image_dir = master_asset_root + "/contents/files/common/image"
    for area_id in result.keys():
        info = result[area_id]
        with open(dst_json_dir + "/areaInfo_"+ area_id + ".json", 'w') as f:
            j = json.dumps({"areaInfo_item":info}, ensure_ascii = False, indent = 4)
            f.write(j.encode("utf-8"))
        for t in ["ground", "wall", "bg"]:
            for i in info[t]:
                d = dst_image_dir + "/" + t
                if not os.path.exists(d):
                    os.makedirs(d)
                shutil.copyfile(src_image_dir+"/common_"+i["image"], d + "/" + i["image"])
# ---
# main function
#
if __name__ == '__main__':
    ll2newLayout("./kms_master_asset", "./kms_tomohiko.furumoto_asset")
    exit(0)

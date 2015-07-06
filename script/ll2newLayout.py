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
    images = {}

    image_dir = "area/test1"
    with open(master_asset_root + "/master_derivatives/master_data.json", 'r') as f:
        master = json.loads(f.read(), object_pairs_hook=OrderedDict)
        for item in master["areaPositionDeprecated"]:
            area_id = item["areaId"]
            result[str(area_id)] = {"areaId":area_id, "ground":[], "wall":[], "bg":[], "position":[]}
        for item in master["layoutDeprecated"]:
            area_id = item["mapID"]
            result[str(area_id)] = {"areaId":area_id, "ground":[], "wall":[], "bg":[], "position":[]}

        for item in master["areaPositionDeprecated"]:
            result[str(item["areaId"])]["position"].append({"id":item["id"],"x":item["x"], "y":item["y"], "z":item["z"]})
        for item in master["layoutDeprecated"]:
            name = item["name"]
            is_ground = item["type"] == "ground"
            is_bg = item["type"] == "bg"
            is_wall = item["type"] == "wall"
            area_id = str(item["mapID"])

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
                        i["width"] = llitem["size"]["width"]
                        i["height"] = llitem["size"]["height"]
                        if is_ground:
                            i["x"] = llitem["position"]["x"] + origin_x
                            i["y"] = llitem["position"]["y"] + origin_z - 400 #TODO FIX magic number

                            i["layer"] = llitem["z"]
                            i["image"] = image_dir + "/ground/" + llitem["image"].replace("common_","")
                            result[area_id]["ground"].append(i)
                        else:
                            i["x"] = llitem["position"]["x"] + origin_x
                            i["y"] = origin_y
                            i["z"] = origin_z + llitem["z"]
                            i["offsetX"] = 0
                            i["offsetY"] = llitem["position"]["y"]
                            if is_wall:
                                i["image"] = image_dir + "/wall/" + llitem["image"].replace("common_","")
                                result[area_id]["wall"].append(i)
                            elif is_bg:
                                i["image"] = image_dir + "/bg/" + llitem["image"].replace("common_","")
                                result[area_id]["bg"].append(i)
                        images[llitem["image"]] = i["image"]

    dst_json_dir = dst_asset_root + "/editor/areaInfo"
    if not os.path.exists(dst_json_dir):
        os.makedirs(dst_json_dir)

    dst_image_dir = dst_asset_root + "/contents/files"
    src_image_dir = master_asset_root + "/contents/files/common/image"
    for area_id in result.keys():
        info = result[area_id]
        with open(dst_json_dir + "/areaInfo_"+ area_id + ".json", 'w') as f:
            j = json.dumps({"areaInfo_item":info}, ensure_ascii = False, indent = 4)
            f.write(j.encode("utf-8"))
    for src, dst in images.items():
        d = os.path.dirname(dst_image_dir + "/" + dst)
        if not os.path.exists(d):
            os.makedirs(d)
        shutil.copyfile(src_image_dir + "/" + src, dst_image_dir + "/" + dst)
# ---
# main function
#
if __name__ == '__main__':
    ll2newLayout("./kms_master_asset", "./kms_tomohiko.furumoto_asset")
    exit(0)

#! /usr/bin/env python
# -*- coding: utf-8 -*-

import os.path
import shutil
import sys
import codecs
import json
import argparse
import datetime
from collections import OrderedDict
from shutil import copy2
import time
import xlrd
import logging
import copy
from logging import info, warning, debug

def searchAndDeleteInListDataRecursiveByKeyAndValue(listData, key, value):
    for data in listData:
        if isinstance(data, dict):
            searchAndDeleteInDictDataRecursiveByKeyAndValue(listData, data, key, value)

def searchAndDeleteInDictDataRecursiveByKeyAndValue(parentList, dictData, key, value):
    if dictData.has_key(key):
        if dictData[key] == value:
            if isinstance(parentList, list):
                index = parentList.index(dictData)
                parentList.pop(index)
                return

    dictKeys = dictData.keys()
    for dictKey in dictKeys:
        child = dictData[dictKey]
        #if isinstance(child, dict):
        #    searchAndDeleteInDictDataRecursiveByKeyAndValue(child, key, value)
        #elif isinstance(child, list):
        if isinstance(child, list):
            searchAndDeleteInListDataRecursiveByKeyAndValue(child, key, value)
            if len(child) == 0:
                dictData.pop(dictKey)


def deleteListByFieldAndName(listData, field, name):
    for data in listData:
        if isinstance(data, dict):
            if data.has_key(field):
                if data[field] == name:
                    listData.remove(data)

def deleteDictRecursiveByName(dictData, name):
    if dictData.has_key(name):
        del dictData[name]
    keys = dictData.keys()
    for key in keys:
        child = dictData[key]
        if isinstance(child, dict):
            deleteDictRecursiveByName(child, name)

def getBoneNameFromSlotName(dictData, slotName):
    if dictData.has_key("slots"):
        slotList = dictData["slots"]
        for slot in slotList:
            if slot.has_key("name"):
                if slot["name"] == slotName:
                    return slot["bone"]
    return ""

def deleteSlotBySlotName(dictData, slotName):
    if dictData.has_key("slots"):
        slotList = dictData["slots"]
        deleteListByFieldAndName(slotList, "name", slotName)

def deleteSkinBySlotName(dictData, slotName):
    if dictData.has_key("skins"):
        skinDict = dictData["skins"]
        deleteDictRecursiveByName(skinDict, slotName)

def deleteAnimationByBoneName(dictData, boneName):
    if dictData.has_key("animations"):
        animationDict = dictData["animations"]
        deleteDictRecursiveByName(animationDict, boneName)

def deleteAnimationBySlotName(dictData, slotName):
    if dictData.has_key("animations"):
        animationDict = dictData["animations"]
        animationKeys = animationDict.keys()
        for animationKey in animationKeys:
            animation = animationDict[animationKey]
            animKeys = animation.keys()
            for animKey in animKeys:
                anim = animation[animKey]
                searchAndDeleteInListDataRecursiveByKeyAndValue(anim, "slot", slotName)
                if isinstance(anim, dict):
                    if anim.has_key(slotName):
                        del anim[slotName]

def deleteElement(json_data, dest_json, boneList, slotList, skinList):
    # 全slotの名前とインデクスを保存
    slotIndexMap = {}
    if json_data.has_key("slots"):
        count = 0
        for slot in json_data["slots"]:
            if isinstance(slot, dict):
                if slot.has_key("name"):
                    slotIndexMap[slot["name"]] = count
                    count += 1

    slotIndexMapAfter = slotIndexMap.copy()

    for boneName in boneList:
        deleteAnimationByBoneName(json_data, boneName)
    for slotName in slotList:
        deleteAnimationBySlotName(json_data, slotName)
        slotIndexMapAfter[slotName] = -1
    for slotName in slotList:
        deleteSlotBySlotName(json_data, slotName)
    for skinName in skinList:
        deleteSkinBySlotName(json_data, skinName)

    count = 0
    slotIndexMapKeys = slotIndexMap.keys()
    for search in range(len(slotIndexMapKeys)):
        for slotIndexMapKey in slotIndexMapKeys:
            if slotIndexMap[slotIndexMapKey] == search:
                if slotIndexMapAfter[slotIndexMapKey] != -1:
                    slotIndexMapAfter[slotIndexMapKey] = count
                    count += 1
                else:
                    slotIndexMapAfter[slotIndexMapKey] = count

    # for slotIndexMapKey in slotIndexMapKeys:
    #    debug("{0} : {1}->{2}".format(slotIndexMapKey, slotIndexMap[slotIndexMapKey], slotIndexMapAfter[slotIndexMapKey]))

    # drawOrderアニメーションのoffsetを付け替える
    if json_data.has_key("animations"):
        animations = json_data["animations"]
        animationsKeys = animations.keys()
        for animationsKey in animationsKeys:
            animation = animations[animationsKey]
            animationKeys = animation.keys()
            for animationKey in animationKeys:
                if animationKey == "drawOrder":
                    drawOrders = animation["drawOrder"]
                    for drawOrder in drawOrders:
                        if drawOrder.has_key("offsets"):
                            offsets = drawOrder["offsets"]
                            for offsetData in offsets:
                                slot = offsetData["slot"]
                                offset = offsetData["offset"]
                                targetIndex = slotIndexMap[slot] + offset
                                targetName = ""
                                currentIndex = 0
                                for slotIndexMapKey in slotIndexMapKeys:
                                    if slotIndexMap[slotIndexMapKey] == targetIndex:
                                        targetName = slotIndexMapKey
                                        break
                                if targetName != "":
                                    offsetData["offset"] = slotIndexMapAfter[targetName] - slotIndexMapAfter[slot]

                                debug("slot:{0} : offset:{1} : index:{2}->{3} : target:{4}:{5}->{6}".format(slot, offset, slotIndexMap[slot], slotIndexMapAfter[slot], targetName, targetIndex, slotIndexMapAfter[targetName]))
                                

        #debug("{0}.{1}->{2}".format(key, slotIndexMap[key], slotIndexMapAfter[key]))

    # spineツール上でテストするために使用しているR_weaponのスキンオフセットを初期化する
    if json_data.has_key("skins"):
        skins = json_data["skins"]
        skinsKeys = skins.keys()
        for skinsKey in skinsKeys:
            skin = skins[skinsKey]
            if skin.has_key("R_weapon"):
                weapon = skin["R_weapon"]
                if weapon.has_key("R_weapon"):
                    weaponData = weapon["R_weapon"]
                    if weaponData.has_key("x"):
                        weaponData["x"] = 0
                    if weaponData.has_key("y"):
                        weaponData["y"] = 0
                    if weaponData.has_key("width"):
                        weaponData["width"] = 0
                    if weaponData.has_key("height"):
                        weaponData["height"] = 0
            if skin.has_key("L_weapon"):
                weapon = skin["L_weapon"]
                if weapon.has_key("L_weapon"):
                    weaponData = weapon["L_weapon"]
                    if weaponData.has_key("x"):
                        weaponData["x"] = 0
                    if weaponData.has_key("y"):
                        weaponData["y"] = 0
                    if weaponData.has_key("width"):
                        weaponData["width"] = 0
                    if weaponData.has_key("height"):
                        weaponData["height"] = 0

    with open(dest_json, 'w+') as f_new:
        info("data created {0}".format(dest_json))
        f_new.write(json.dumps(json_data))

def completeSpine(srcPath, dstPath):
    src, ext = os.path.splitext(srcPath)
    dst, ext = os.path.splitext(dstPath)
    base = os.path.join(os.path.dirname(srcPath), os.path.basename(dst))

    # png
    if not os.path.exists(base + '.png'):
        info("complete png: {0}.png -> {1}.png".format(src, dst))
        copy2(src+'.png', dst+'.png')

    # modify png filename in .atlas
    if not os.path.exists(base + '.atlas'):
        info("complete atlas: {0}.atlas -> {1}.atlas".format(src, dst))
        contents = []
        with open(src + '.atlas', 'r') as f:
            for l in f.readlines():
                contents.append(l.replace(os.path.basename(src)+'.png', os.path.basename(dst)+'.png'))
        with open(dst + '.atlas', 'w') as f:
            f.writelines(contents)
    
def getConvertParam(hasTwinTail, hasPonyTail, hasEarCat, hasEarRabbit, hasTail, hasEar, hasMant, hasInside, hasShoulder):
    slot = []
    bone = []
    # if hasTwinTail:
    #     slot.append("C_hd_hair_b")
    # else:
    if not hasTwinTail:
        slot.append("C_hd_twintail_R")
        slot.append("C_hd_twintail_L")
        bone.append("twintail_L1")
        bone.append("twintail_R1")

    # if hasPonyTail:
    #     slot.append("C_hd_hair_b")
    # else:
    if not hasPonyTail:
        slot.append("C_hd_hair_tail")
        bone.append("hair_tail")

    if not hasEarCat:
        slot.append("C_cat_ear")
        bone.append("cat_earRight1")
        bone.append("cat_earLeft1")

    if not hasEarRabbit:
        slot.append("C_rabbit_ear")
        bone.append("rabbit_earLeft1")
        bone.append("rabbit_earLeft1")

    if not hasTail:
        slot.append("C_tail")
        bone.append("tail")

    if not hasEar:
        slot.append("C_hd_ear")

    if not hasMant:
        slot.append("C_bo_mant_b")

    if not hasInside:
        slot.append("C_bo_gear_inside")

    if not hasShoulder:
        slot.append("L_shoulder")

    return (slot, bone);

def export_spine(master_excel, sheet_name, start_row, start_column, input_json, output_dir):
    info("master excel = %s:%s" % (master_excel, sheet_name))
    info("start %s:%s" % (start_row, start_column))

    json_data = OrderedDict()
    with open(input_json, 'r') as f:
        json_data = json.loads(f.read(), object_pairs_hook=OrderedDict)

    start_row = int(start_row)
    start_col = -1
    book = xlrd.open_workbook(master_excel)
    sheet = book.sheet_by_name(sheet_name)

    if sheet.nrows > 0:
        for col in range(sheet.ncols):
            if sheet.cell_value(0, col) == start_column:
                start_col = col
                debug("find {0}:{1}".format(start_column, col))
                break

    if start_col >= 0:
        for row in range(sheet.nrows):
            if (sheet.ncols < start_col+9):
                info("ncols={0} but paramStartCol={1}".format(sheet.ncols, start_col))
            else:
                if (row >= start_row):
                    model_id = int(sheet.cell_value(row, 0))
                    hasTwinTail = sheet.cell_value(row, start_col)
                    hasPonyTail = sheet.cell_value(row, start_col+1)
                    hasEarCat = sheet.cell_value(row, start_col+2)
                    hasEarRabitt = sheet.cell_value(row, start_col+3)
                    hasTail = sheet.cell_value(row, start_col+4)
                    hasEar = sheet.cell_value(row, start_col+5)
                    hasMant = sheet.cell_value(row, start_col+6)
                    hasInside = sheet.cell_value(row, start_col+7)
                    hasShoulder = sheet.cell_value(row, start_col+8)
                    debug("Convert Param = {0}:{1},{2},{3},{4},{5},{6},{7},{8},{9}".format(str(model_id), hasTwinTail, hasPonyTail, hasEarCat, hasEarRabitt, hasTail, hasEar, hasMant, hasInside, hasShoulder))
                    slot, bone = getConvertParam(hasTwinTail, hasPonyTail, hasEarCat, hasEarRabitt, hasTail, hasEar, hasMant, hasInside, hasShoulder)
                    skin = slot

                    root, ext = os.path.splitext(input_json)
                    dest_json = os.path.abspath(output_dir) + "/" + str(model_id) + ext

                    debug("output file = {0}".format(dest_json))
                    debug("bones = {0}".format(bone))
                    debug("slots = {0}".format(slot))
                    debug("skins = {0}".format(skin))
                    deleteElement(copy.deepcopy(json_data), dest_json, slot, bone, skin)
                    completeSpine(input_json, dest_json)

def verify_spine(input_json, size_limit):
    limits = []
    for l in size_limit.split(':'):
        limits.append(float(l))
    with open(input_json, 'r') as f:
        spine = json.load(f, object_pairs_hook=OrderedDict)

    width  = float(spine['skeleton']['width'])
    height = float(spine['skeleton']['height'])
    if width < limits[0] or limits[1] < width:
        raise Exception("spine skeleton.width is invalid: %s < %s < %s: %s" % (limits[0], width, limits[1], input_json))
    if height < limits[0] or limits[1] < height:
        raise Exception("spine skeleton.height is invalid: %s < %s < %s: %s" % (limits[0], height, limits[1], input_json))

    return True

# ---
# main function
#
if __name__ == '__main__':
    sys.stdout = codecs.lookup('utf_8')[-1](sys.stdout)
    parser = argparse.ArgumentParser(
        description = 'delete specified elements from source spine json file by excel sheet data',
        epilog = 'e.g. > python delete-element.py master/character.xlsx characterSpine 3 9 contents/files/spine/characterSpine/character.json contents/files/spine/characterSpine/'
    )
    parser.add_argument('master_excel', help = 'input master data excel')
    parser.add_argument('sheet_name',   help = 'target sheet name to use in master_excel')
    parser.add_argument('start_row',    help = 'start row number in target sheet')
    parser.add_argument('start_column', help = 'start column name in target sheet')
    parser.add_argument('input_json',   help = 'source spine json file')
    parser.add_argument('output_dir',   help = 'dest spine jsons dir')
    parser.add_argument('--size-limit', help = "spine size spiecified by max-width:max-height")
    parser.add_argument('--log-level',  help = 'log level (WARNING|INFO|DEBUG). default: INFO')
    args = parser.parse_args()
    logging.basicConfig(level = args.log_level or "INFO", format = '%(asctime)-15s %(levelname)s %(message)s')

    if args.size_limit:
        verify_spine(args.input_json, args.size_limit)
    export_spine(args.master_excel, args.sheet_name, args.start_row, args.start_column, args.input_json, args.output_dir)


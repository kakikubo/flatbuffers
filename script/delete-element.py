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
"""
def exportWearPattern(parser, name, dirName):
    srcPath = os.path.abspath(dirName)
    dstPath = os.path.abspath(dirName)
    wearNames = [name + "_n", name + "_w"]
    deleteElement(parser.parse_args(["-i", srcPath, "-o", dstPath + "/" + wearNames[0], "-f", name, "-s", "C_bo_gear_inside", "-b"]))
    shutil.copy(srcPath + "/" + name + ".json", dstPath + "/" + wearNames[1] + ".json")
    shutil.copy(srcPath + "/" + name + ".atlas", dstPath + "/" + wearNames[1] + ".atlas")
    return wearNames

def exportWingPattern(parser, name, dirName):
    srcPath = os.path.abspath(dirName)
    dstPath = os.path.abspath(dirName)
    wingNames = [name + "_n", name + "_w"]
    deleteElement(parser.parse_args(["-i", srcPath, "-o", dstPath + "/" + wingNames[0], "-f", name, "-s", "C_bo_mant_b", "-b"]))
    shutil.copy(srcPath + "/" + name + ".json", dstPath + "/" + wingNames[1] + ".json")
    shutil.copy(srcPath + "/" + name + ".atlas", dstPath + "/" + wingNames[1] + ".atlas")
    return wingNames

def exportAccessoryPattern(parser, name, dirName):
    srcPath = os.path.abspath(dirName)
    dstPath = os.path.abspath(dirName)
    accessoryNames = [name + "_c", name + "_r", name + "_n"]
    deleteElement(parser.parse_args(["-i", srcPath, "-o", dstPath + "/" + accessoryNames[0], "-f", name, "-s", "C_rabbit_ear", "-b", "rabbit_earLeft1", "rabbit_earLeft1"]))
    deleteElement(parser.parse_args(["-i", srcPath, "-o", dstPath + "/" + accessoryNames[1], "-f", name, "-s", "C_cat_ear", "C_tail", "-b", "cat_earRight1", "cat_earLeft1", "tail"]))
    deleteElement(parser.parse_args(["-i", srcPath, "-o", dstPath + "/" + accessoryNames[2], "-f", name, "-s", "C_rabbit_ear", "C_cat_ear", "C_tail", "-b", "rabbit_earLeft1", "rabbit_earLeft1", "cat_earRight1", "cat_earLeft1", "tail"]))
    return accessoryNames

def exportWithoutAccessory(parser, name, dirName):
    srcPath = os.path.abspath(dirName)
    dstPath = os.path.abspath(dirName)
    accessoryNames = [name + "_n"]
    deleteElement(parser.parse_args(["-i", srcPath, "-o", dstPath + "/" + accessoryNames[0], "-f", name, "-s", "C_rabbit_ear", "C_cat_ear", "C_tail", "-b", "rabbit_earLeft1", "rabbit_earLeft1", "cat_earRight1", "cat_earLeft1", "tail"]))
    return accessoryNames

def exportHairPattern(parser, name, dirName):
    srcPath = os.path.abspath(dirName)
    dstPath = os.path.abspath(dirName)
    hairNames = [name + "_b", name + "_p", name + "_t"]
    deleteElement(parser.parse_args(["-i", srcPath, "-o", dstPath + "/" + hairNames[0], "-f", name, "-s", "C_hd_twintail_R", "C_hd_twintail_L", "C_hd_hair_tail", "-b", "twintail_L1", "twintail_R1", "hair_tail"]))
    deleteElement(parser.parse_args(["-i", srcPath, "-o", dstPath + "/" + hairNames[1], "-f", name, "-s", "C_hd_twintail_R", "C_hd_twintail_L", "C_hd_hair_b", "-b", "twintail_L1", "twintail_R1"]))
    deleteElement(parser.parse_args(["-i", srcPath, "-o", dstPath + "/" + hairNames[2], "-f", name, "-s", "C_hd_hair_tail", "C_hd_hair_b", "-b", "hair_tail"]))
    return hairNames

def exportWithoutHair(parser, name, dirName):
    srcPath = os.path.abspath(dirName)
    dstPath = os.path.abspath(dirName)
    hairNames = [name + "_b"]
    deleteElement(parser.parse_args(["-i", srcPath, "-o", dstPath + "/" + hairNames[0], "-f", name, "-s", "C_hd_twintail_R", "C_hd_twintail_L", "C_hd_hair_tail", "-b", "twintail_L1", "twintail_R1", "hair_tail"]))
    return hairNames

def autoExport(parser, name, dirName):
    wearNames = exportWearPattern(parser, name, dirName)
    for wearName in wearNames:
        wingNames = exportWingPattern(parser, wearName, dirName)
        for wingName in wingNames:
            accessoryNames = exportAccessoryPattern(parser, wingName, dirName)
            for accessoryName in accessoryNames:
                hairNames = exportHairPattern(parser, accessoryName, dirName)
"""

def deleteElement(args):
    srcJson = os.path.abspath(args.input_json)
    dstJson = os.path.abspath(args.output_json)

    boneList = args.delete_bone
    slotList = args.delete_slot
    skinList = slotList

    debug("convert file = {0}".format(srcJson))
    debug("output file = {0}".format(dstJson))
    debug("bones = {0}".format(boneList))
    debug("slots = {0}".format(slotList))
    debug("skins = {0}".format(skinList))

    jsonData = OrderedDict()
    with open(srcJson, 'r') as f:
        jsonData = json.loads(f.read(), object_pairs_hook=OrderedDict)

        # 全slotの名前とインデクスを保存
        slotIndexMap = {}
        if jsonData.has_key("slots"):
            count = 0
            for slot in jsonData["slots"]:
                if isinstance(slot, dict):
                    if slot.has_key("name"):
                        slotIndexMap[slot["name"]] = count
                        count += 1

        slotIndexMapAfter = slotIndexMap.copy()

        for boneName in boneList:
            deleteAnimationByBoneName(jsonData, boneName)
        for slotName in slotList:
            deleteAnimationBySlotName(jsonData, slotName)
            slotIndexMapAfter[slotName] = -1
        for slotName in slotList:
            deleteSlotBySlotName(jsonData, slotName)
        for skinName in skinList:
            deleteSkinBySlotName(jsonData, skinName)

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
        if jsonData.has_key("animations"):
            animations = jsonData["animations"]
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
        if jsonData.has_key("skins"):
            skins = jsonData["skins"]
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

    changed = True
    if os.path.exists(dstJson):
        with open(dstJson, 'r') as f_old:
            dstData = json.loads(f_old.read(), object_pairs_hook=OrderedDict)
            if jsonData == dstData:
                info("data not changed:{0}".format(dstJson))
                changed = False
            else:
                os.remove(dstJson)

    if changed:
        with open(dstJson, 'w+') as f_new:
            info("data created {0}".format(dstJson))
            #f_new.write(json.dumps(jsonData, indent=2))
            f_new.write(json.dumps(jsonData))

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
                contents.append(l.replace(src+'.png', dst+'.png'))
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

    dic = {}
    dic["slot"] = slot
    dic["bone"] = bone
    return dic

def export_spine(parser, master_excel, sheet_name, start_row, start_column, input_json, output_dir):
    info("master excel = %s:%s" % (master_excel, sheet_name))
    info("start %s:%s" % (start_row, start_column))

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
                    modelID = int(sheet.cell_value(row, 0))
                    hasTwinTail = sheet.cell_value(row, start_col)
                    hasPonyTail = sheet.cell_value(row, start_col+1)
                    hasEarCat = sheet.cell_value(row, start_col+2)
                    hasEarRabitt = sheet.cell_value(row, start_col+3)
                    hasTail = sheet.cell_value(row, start_col+4)
                    hasEar = sheet.cell_value(row, start_col+5)
                    hasMant = sheet.cell_value(row, start_col+6)
                    hasInside = sheet.cell_value(row, start_col+7)
                    hasShoulder = sheet.cell_value(row, start_col+8)
                    debug("Convert Param = {0}:{1},{2},{3},{4},{5},{6},{7},{8},{9}".format(str(modelID), hasTwinTail, hasPonyTail, hasEarCat, hasEarRabitt, hasTail, hasEar, hasMant, hasInside, hasShoulder))
                    dic = getConvertParam(hasTwinTail, hasPonyTail, hasEarCat, hasEarRabitt, hasTail, hasEar, hasMant, hasInside, hasShoulder)
                    srcPath = os.path.abspath(input_json)
                    root, ext = os.path.splitext(input_json)
                    dstPath = os.path.abspath(output_dir) + "/" + str(modelID) + ext

                    params = []
                    params.append("-i")
                    params.append(srcPath)
                    params.append("-o")
                    params.append(dstPath)
                    params.append("-s")
                    for slot in dic["slot"]:
                        params.append(slot)
                    params.append("-b")
                    for bone in dic["bone"]:
                        params.append(bone)
                    debug(params)
                    deleteElement(parser.parse_args(params))
                    completeSpine(srcPath, dstPath)

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
    argv = sys.argv
    argc = len(argv)

    internal_parser = argparse.ArgumentParser(
        description = 'delete specified elements from source spine json file',
    )
    internal_parser.add_argument("-i", '--input-json',  required=True, help = "input spine json")
    internal_parser.add_argument("-o", '--output-json', required=True, help = "output spine json")
    internal_parser.add_argument("-b", '--delete-bone', nargs="*", help="slot list to delete")
    internal_parser.add_argument("-s", '--delete-slot', nargs="*", help="bone list to delete")

    if argc < 7:
        deleteElement(internal_parser.parse_args())
    else:
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
        export_spine(internal_parser, args.master_excel, args.sheet_name, args.start_row, args.start_column, args.input_json, args.output_dir)


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
import time
import xlrd
import logging
from logging import info, warning, debug

def searchInListDataRecursiveByKeyAndValue(listData, key, value):
    for data in listData:
        if isinstance(data, dict):
            return searchInDictDataRecursiveByKeyAndValue(data, key, value)


def searchInDictDataRecursiveByKeyAndValue(dictData, key, value):
    if dictData.has_key(key):
        if dictData[key] == value:
            return True
    dictKeys = dictData.keys()
    for dictKey in dictKeys:
        child = dictData[dictKey]
        if isinstance(child, dict):
            return searchInDictDataRecursiveByKeyAndValue(child, key, value)
        elif isinstance(child, list):
            return searchInListDataRecursiveByKeyAndValue(child, key, value)
    return False


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
                if searchInListDataRecursiveByKeyAndValue(anim, "slot", slotName):
                    del animation[animKey]
                if isinstance(anim, dict):
                    if anim.has_key(slotName):
                        del anim[slotName]
"""
def exportWearPattern(name, dirName):
    srcPath = os.path.abspath(dirName)
    dstPath = os.path.abspath(dirName)
    wearNames = [name + "_n", name + "_w"]
    parser = argparse.ArgumentParser()
    parser.add_argument("-s", nargs="*")
    parser.add_argument("-b", nargs="*")
    parser.add_argument("-i", required=True)
    parser.add_argument("-o", required=True)
    parser.add_argument("-f", required=True)
    deleteElement(parser.parse_args(["-i", srcPath, "-o", dstPath + "/" + wearNames[0], "-f", name, "-s", "C_bo_gear_inside", "-b"]))
    shutil.copy(srcPath + "/" + name + ".json", dstPath + "/" + wearNames[1] + ".json")
    shutil.copy(srcPath + "/" + name + ".atlas", dstPath + "/" + wearNames[1] + ".atlas")
    return wearNames

def exportWingPattern(name, dirName):
    srcPath = os.path.abspath(dirName)
    dstPath = os.path.abspath(dirName)
    wingNames = [name + "_n", name + "_w"]
    parser = argparse.ArgumentParser()
    parser.add_argument("-s", nargs="*")
    parser.add_argument("-b", nargs="*")
    parser.add_argument("-i", required=True)
    parser.add_argument("-o", required=True)
    parser.add_argument("-f", required=True)
    deleteElement(parser.parse_args(["-i", srcPath, "-o", dstPath + "/" + wingNames[0], "-f", name, "-s", "C_bo_mant_b", "-b"]))
    shutil.copy(srcPath + "/" + name + ".json", dstPath + "/" + wingNames[1] + ".json")
    shutil.copy(srcPath + "/" + name + ".atlas", dstPath + "/" + wingNames[1] + ".atlas")
    return wingNames

def exportAccessoryPattern(name, dirName):
    srcPath = os.path.abspath(dirName)
    dstPath = os.path.abspath(dirName)
    accessoryNames = [name + "_c", name + "_r", name + "_n"]
    parser = argparse.ArgumentParser()
    parser.add_argument("-s", nargs="*")
    parser.add_argument("-b", nargs="*")
    parser.add_argument("-i", required=True)
    parser.add_argument("-o", required=True)
    parser.add_argument("-f", required=True)
    deleteElement(parser.parse_args(["-i", srcPath, "-o", dstPath + "/" + accessoryNames[0], "-f", name, "-s", "C_rabbit_ear", "-b", "rabbit_earLeft1", "rabbit_earLeft1"]))
    deleteElement(parser.parse_args(["-i", srcPath, "-o", dstPath + "/" + accessoryNames[1], "-f", name, "-s", "C_cat_ear", "C_tail", "-b", "cat_earRight1", "cat_earLeft1", "tail"]))
    deleteElement(parser.parse_args(["-i", srcPath, "-o", dstPath + "/" + accessoryNames[2], "-f", name, "-s", "C_rabbit_ear", "C_cat_ear", "C_tail", "-b", "rabbit_earLeft1", "rabbit_earLeft1", "cat_earRight1", "cat_earLeft1", "tail"]))
    return accessoryNames

def exportWithoutAccessory(name, dirName):
    srcPath = os.path.abspath(dirName)
    dstPath = os.path.abspath(dirName)
    parser = argparse.ArgumentParser()
    accessoryNames = [name + "_n"]
    parser.add_argument("-s", nargs="*")
    parser.add_argument("-b", nargs="*")
    parser.add_argument("-i", required=True)
    parser.add_argument("-o", required=True)
    parser.add_argument("-f", required=True)
    deleteElement(parser.parse_args(["-i", srcPath, "-o", dstPath + "/" + accessoryNames[0], "-f", name, "-s", "C_rabbit_ear", "C_cat_ear", "C_tail", "-b", "rabbit_earLeft1", "rabbit_earLeft1", "cat_earRight1", "cat_earLeft1", "tail"]))
    return accessoryNames

def exportHairPattern(name, dirName):
    srcPath = os.path.abspath(dirName)
    dstPath = os.path.abspath(dirName)
    hairNames = [name + "_b", name + "_p", name + "_t"]
    parser = argparse.ArgumentParser()
    parser.add_argument("-s", nargs="*")
    parser.add_argument("-b", nargs="*")
    parser.add_argument("-i", required=True)
    parser.add_argument("-o", required=True)
    parser.add_argument("-f", required=True)
    deleteElement(parser.parse_args(["-i", srcPath, "-o", dstPath + "/" + hairNames[0], "-f", name, "-s", "C_hd_twintail_R", "C_hd_twintail_L", "C_hd_hair_tail", "-b", "twintail_L1", "twintail_R1", "hair_tail"]))
    deleteElement(parser.parse_args(["-i", srcPath, "-o", dstPath + "/" + hairNames[1], "-f", name, "-s", "C_hd_twintail_R", "C_hd_twintail_L", "C_hd_hair_b", "-b", "twintail_L1", "twintail_R1"]))
    deleteElement(parser.parse_args(["-i", srcPath, "-o", dstPath + "/" + hairNames[2], "-f", name, "-s", "C_hd_hair_tail", "C_hd_hair_b", "-b", "hair_tail"]))
    return hairNames

def exportWithoutHair(name, dirName):
    srcPath = os.path.abspath(dirName)
    dstPath = os.path.abspath(dirName)
    hairNames = [name + "_b"]
    parser = argparse.ArgumentParser()
    parser.add_argument("-s", nargs="*")
    parser.add_argument("-b", nargs="*")
    parser.add_argument("-i", required=True)
    parser.add_argument("-o", required=True)
    parser.add_argument("-f", required=True)
    deleteElement(parser.parse_args(["-i", srcPath, "-o", dstPath + "/" + hairNames[0], "-f", name, "-s", "C_hd_twintail_R", "C_hd_twintail_L", "C_hd_hair_tail", "-b", "twintail_L1", "twintail_R1", "hair_tail"]))
    return hairNames

def autoExport(name, dirName):
    wearNames = exportWearPattern(name, dirName)
    for wearName in wearNames:
        wingNames = exportWingPattern(wearName, dirName)
        for wingName in wingNames:
            accessoryNames = exportAccessoryPattern(wingName, dirName)
            for accessoryName in accessoryNames:
                hairNames = exportHairPattern(accessoryName, dirName)
"""

# ---
# default help message
#
def printHelp():
    print '''> python delete-element.py {excelFilePath} {excelSheetName} {startRow} {startCol} {spineFilePath} {outPutFolderPath}
    e.g. > python delete-element.py master/character.xlsx characterSpine 3 9 contents/files/spine/characterSpine/character.json contents/files/spine/characterSpine/'''

def deleteElement(args):
    srcPath = os.path.abspath(args.i)
    dstPath = os.path.abspath(args.o)
    srcJson = srcPath
    dstJson = dstPath

    boneList = args.b
    slotList = args.s
    skinList = slotList

    if True:
        debug("convert file = {0}".format(srcJson))
        debug("output file = {0}".format(dstJson))
        debug("bones = {0}".format(boneList))
        debug("slots = {0}".format(slotList))
        debug("skins = {0}".format(skinList))

    jsonData = {}
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

        # spineツール上でテストするために使用しているR_weaponのオフセットを初期化する
        if jsonData.has_key("bones"):
            bonesList = jsonData["bones"]
            for bone in bonesList:
                if bone.has_key("name"):
                    if bone["name"] == "R_weapon":
                        if bone.has_key("x"):
                            bone["x"] = 0
                        if bone.has_key("y"):
                            bone["y"] = 0

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
            #f.write(json.dumps(jsonData, indent=2, sort_keys=False))
            f_new.write(json.dumps(jsonData))
    
def getConvertParam(hasTwinTail, hasPonyTail, hasEarCat, hasEarRabbit, hasTail):
    slot = []
    bone = []
    if hasTwinTail:
        slot.append("C_hd_hair_b")
    else:
        slot.append("C_hd_twintail_R")
        slot.append("C_hd_twintail_L")
        bone.append("twintail_L1")
        bone.append("twintail_R1")

    if hasPonyTail:
        slot.append("C_hd_hair_b")
    else:
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

    dic = {}
    dic["slot"] = slot
    dic["bone"] = bone
    return dic

def exportSpine(masterExcel, sheetName, paramStartRow, paramStartField, srcFile, outPath):
    iParamStartRow = int(paramStartRow)
    iParamStartCol = -1
    book = xlrd.open_workbook(masterExcel)
    sheet = book.sheet_by_name(sheetName)

    if sheet.nrows > 0:
        for col in range(sheet.ncols):
            if sheet.cell_value(0, col) == paramStartField:
                iParamStartCol = col
                debug("find {0}:{1}".format(paramStartField, col))
                break

    if iParamStartCol >= 0:
        for row in range(sheet.nrows):
            if (sheet.ncols < iParamStartCol+5):
                debug("ncols={0} but paramStartCol={1}".format(sheet.ncols, iParamStartCol))
            else:
                if (row >= iParamStartRow):
                    modelID = int(sheet.cell_value(row, 0))
                    hasTwinTail = sheet.cell_value(row, iParamStartCol)
                    hasPonyTail = sheet.cell_value(row, iParamStartCol+1)
                    hasEarCat = sheet.cell_value(row, iParamStartCol+2)
                    hasEarRabitt = sheet.cell_value(row, iParamStartCol+3)
                    hasTail = sheet.cell_value(row, iParamStartCol+4)
                    debug("Convert Param = {0}:{1},{2},{3},{4},{5}".format(str(modelID), hasTwinTail, hasPonyTail, hasEarCat, hasEarRabitt, hasTail))
                    dic = getConvertParam(hasTwinTail, hasPonyTail, hasEarCat, hasEarRabitt, hasTail)
                    srcPath = os.path.abspath(srcFile)
                    root, ext = os.path.splitext(srcFile)
                    dstPath = os.path.abspath(outPath) + "/" + str(modelID) + ext

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
                    parser = argparse.ArgumentParser()
                    parser.add_argument("-s", nargs="*")
                    parser.add_argument("-b", nargs="*")
                    parser.add_argument("-i", required=True)
                    parser.add_argument("-o", required=True)
                    deleteElement(parser.parse_args(params))

# ---
# main function
#
if __name__ == '__main__':
    log_level = "INFO" # "DEBUG" # FIXME get via arguments
    logging.basicConfig(level = log_level, format = '%(asctime)-15s %(levelname)s %(message)s')
    sys.stdout = codecs.lookup('utf_8')[-1](sys.stdout)
    argv = sys.argv
    argc = len(argv)

    if argc > 1:
        if argv[1] == "-h":
            printHelp()
        else:
            if argc == 7:
                exportSpine(argv[1], argv[2], argv[3], argv[4], argv[5], argv[6])
            elif argc == 5:
                parser = argparse.ArgumentParser()
                parser.add_argument("-s", nargs="*")
                parser.add_argument("-b", nargs="*")
                parser.add_argument("-i", required=True)
                parser.add_argument("-o", required=True)
                deleteElement(parser.parse_args())
            else:
                print 'Error :: not enough params.'
                printHelp()
    else:
        printHelp()


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

CURRENT_CATEGORY_DEPTH = 0
CURRENT_CATEGORY = "NONE"
RELAED_TARGET = []

SLOT_NAME = ""
BONE_NAME = ""

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
    deleteElementBySlotsName(parser.parse_args(["-i", srcPath, "-o", dstPath + "/" + wearNames[0], "-f", name, "-s", "C_bo_gear_inside", "-b"]))
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
    deleteElementBySlotsName(parser.parse_args(["-i", srcPath, "-o", dstPath + "/" + wingNames[0], "-f", name, "-s", "C_bo_mant_b", "-b"]))
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
    deleteElementBySlotsName(parser.parse_args(["-i", srcPath, "-o", dstPath + "/" + accessoryNames[0], "-f", name, "-s", "C_rabbit_ear", "-b", "rabbit_earLeft1", "rabbit_earLeft1"]))
    deleteElementBySlotsName(parser.parse_args(["-i", srcPath, "-o", dstPath + "/" + accessoryNames[1], "-f", name, "-s", "C_cat_ear", "C_tail", "-b", "cat_earRight1", "cat_earLeft1", "tail"]))
    deleteElementBySlotsName(parser.parse_args(["-i", srcPath, "-o", dstPath + "/" + accessoryNames[2], "-f", name, "-s", "C_rabbit_ear", "C_cat_ear", "C_tail", "-b", "rabbit_earLeft1", "rabbit_earLeft1", "cat_earRight1", "cat_earLeft1", "tail"]))
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
    deleteElementBySlotsName(parser.parse_args(["-i", srcPath, "-o", dstPath + "/" + hairNames[0], "-f", name, "-s", "C_hd_twintail_R", "C_hd_twintail_L", "C_hd_hair_tail", "-b", "twintail_L1", "twintail_R1", "hair_tail"]))
    deleteElementBySlotsName(parser.parse_args(["-i", srcPath, "-o", dstPath + "/" + hairNames[1], "-f", name, "-s", "C_hd_twintail_R", "C_hd_twintail_L", "C_hd_hair_b", "-b", "twintail_L1", "twintail_R1"]))
    deleteElementBySlotsName(parser.parse_args(["-i", srcPath, "-o", dstPath + "/" + hairNames[2], "-f", name, "-s", "C_hd_hair_tail", "C_hd_hair_b", "-b", "hair_tail"]))
    return hairNames

def exportWeaponPattern(name, dirName):
    srcPath = os.path.abspath(dirName)
    dstPath = os.path.abspath(dirName)
    weaponNames = [name + "_1", name + "_2", name + "_3", name + "_4", name + "_5"]
    parser = argparse.ArgumentParser()
    parser.add_argument("-s", nargs="*")
    parser.add_argument("-b", nargs="*")
    parser.add_argument("-i", required=True)
    parser.add_argument("-o", required=True)
    parser.add_argument("-f", required=True)
    deleteElementBySlotsName(parser.parse_args(["-i", srcPath, "-o", dstPath + "/" + weaponNames[0], "-f", name, "-s", "R_weapon_2", "R_weapon_3", "R_weapon_4", "R_weapon_5", "-b"]))
    deleteElementBySlotsName(parser.parse_args(["-i", srcPath, "-o", dstPath + "/" + weaponNames[1], "-f", name, "-s", "R_weapon_1", "R_weapon_3", "R_weapon_4", "R_weapon_5", "-b"]))
    deleteElementBySlotsName(parser.parse_args(["-i", srcPath, "-o", dstPath + "/" + weaponNames[2], "-f", name, "-s", "R_weapon_1", "R_weapon_2", "R_weapon_4", "R_weapon_5", "-b"]))
    deleteElementBySlotsName(parser.parse_args(["-i", srcPath, "-o", dstPath + "/" + weaponNames[3], "-f", name, "-s", "R_weapon_1", "R_weapon_2", "R_weapon_3", "R_weapon_5", "-b"]))
    deleteElementBySlotsName(parser.parse_args(["-i", srcPath, "-o", dstPath + "/" + weaponNames[4], "-f", name, "-s", "R_weapon_1", "R_weapon_2", "R_weapon_3", "R_weapon_4", "-b"]))
    return weaponNames

# ---
# default help message
#
def printHelp():
    print '''Error :: not enough params.
    e.g. > python delete-element.py test.json slotName1 slotName2 slotName3'''

def deleteElementBySlotsName(args):
    srcPath = os.path.abspath(args.i)
    dstPath = os.path.abspath(args.o)
    srcJson = srcPath + "/" + args.f + ".json"
    dstJson = dstPath + ".json"
    srcAtlas = srcPath + "/" + args.f + ".atlas"
    dstAtlas = dstPath + ".atlas"

    boneList = args.b
    slotList = args.s
    skinList = slotList

    if True:
        print "convert file = {0}".format(srcJson)
        print "output file = {0}".format(dstJson)
        print "bones = {0}".format(boneList)
        print "slots = {0}".format(slotList)
        print "skins = {0}".format(skinList)
        print "copy file = {0} to {1}".format(srcAtlas, dstAtlas)

    with open(srcJson, 'r') as f:
        jsonData = json.loads(f.read(), object_pairs_hook=OrderedDict)
        for boneName in boneList:
            deleteAnimationByBoneName(jsonData, boneName)
        for slotName in slotList:
            deleteAnimationBySlotName(jsonData, slotName)
        for slotName in slotList:
            deleteSlotBySlotName(jsonData, slotName)
        for skinName in skinList:
            deleteSkinBySlotName(jsonData, skinName)

    with open(dstJson, 'w') as f:
        f.write(json.dumps(jsonData, indent=2, sort_keys=False))
    shutil.copy(srcAtlas, dstAtlas)

def autoExport(name, dirName):
    wearNames = exportWearPattern(name, dirName)
    for wearName in wearNames:
        wingNames = exportWingPattern(wearName, dirName)
        for wingName in wingNames:
            accessoryNames = exportAccessoryPattern(wingName, dirName)
            for accessoryName in accessoryNames:
                hairNames = exportHairPattern(accessoryName, dirName)
                for hairName in hairNames:
                    weaponNames = exportWeaponPattern(hairName, dirName)

# ---
# main function
#
if __name__ == '__main__':
    sys.stdout = codecs.lookup('utf_8')[-1](sys.stdout)
    argv = sys.argv
    argc = len(argv)
    if argc < 4:
        if argc == 3:
            # e.g. > cd testdata (chara.json & chara.atlas are existing in testdata folder.)
            #      > python ${KMS_SCRIPT}/delete-element.py chara ./ (convert "chara.json". output in "./" folder)
            autoExport(argv[1], argv[2])
        else:
            printHelp()
    else:
        parser = argparse.ArgumentParser()
        parser.add_argument("-s", nargs="*")
        parser.add_argument("-b", nargs="*")
        parser.add_argument("-i", required=True)
        parser.add_argument("-o", required=True)
        parser.add_argument("-f", required=True)
        deleteElementBySlotsName(parser.parse_args())

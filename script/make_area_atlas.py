#! /usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import codecs
import subprocess
import shutil

def getFileNum(dir):
    if not os.path.isdir(dir): return 0
    i=0
    for root, dirs, files in os.walk(dir):
        i+=len(files)
    return i

def makeAreaAtlas(srcFolderPath, dstFolderPath):
    print "src:{0}".format(srcFolderPath)
    print "dst:{0}".format(dstFolderPath)
    print "\n"
    topDirs = os.listdir(srcFolderPath)
    for topDir in topDirs:
        categoryPath = "{0}/{1}".format(srcFolderPath, topDir)
        if not os.path.isdir(categoryPath):
            continue
        if topDir == "test1":
            continue
        categoryDirs = os.listdir(categoryPath)
        for categoryDir in categoryDirs:
            # フォルダ階層も名前に含みたいので作業フォルダにコピーしてからコンバートする
            srcDir = "{0}/{1}/{2}".format(srcFolderPath, topDir, categoryDir)
            if not os.path.isdir(srcDir):
                continue

            workTopDir = dstFolderPath + "/_temp"
            if os.path.isdir(workTopDir):
                shutil.rmtree(workTopDir)
            dstDir = workTopDir + "/" + topDir + "/" + categoryDir
            shutil.copytree(srcDir, dstDir)

            base = "{0}/{1}/{1}_{2}".format(dstFolderPath, topDir, categoryDir)

            plistFile = base + "_{n}.png.plist"
            imageFile = base + "_{n}.png"
            textureType = "png"
            textureFormat = "RGBA8888"
            pvrQuality = "very-low"
            scale = "1.0"

            fnum = getFileNum(workTopDir)
            print "{0} : textures num[{1}]".format(srcDir, fnum)
            if fnum == 0:
                continue

            subprocess.check_call(["TexturePacker",
                "--sheet", imageFile,
                "--texture-format", textureType,
                "--format", "cocos2d",
                "--data", plistFile,
                "--algorithm", "MaxRects",
                "--maxrects-heuristics", "Best",
                "--basic-sort-by", "Best",
                "--basic-order", "Ascending",
                "--max-size", "2048",
                "--size-constraints", "POT",
                "--force-squared",
                "--force-word-aligned",
                "--pack-mode", "Best",
                "--multipack",
                "--common-divisor-x", "4",
                "--common-divisor-y", "4",
                "--shape-padding", "2",
                "--border-padding", "2",
                "--enable-rotation",
                "--trim-mode", "None",
                # "--disable-clean-transparency",
                "--opt", textureFormat,
                "--pvr-quality", pvrQuality,
                # "--premultiply-alpha",
                "--png-opt-level", "0",
                "--extrude", "4",
                "--scale", scale,
                "--scale-mode", "Smooth",
                 workTopDir])

            plistFile = base + "_{n}.pvr.plist"
            imageFile = base + "_{n}.pvr.ccz"
            textureType = "pvr3ccz"
            textureFormat = "PVRTC4"
            pvrQuality = "very-low"
            #pvrQuality = "best"
            scale = "1.0"

            """
            subprocess.check_call(["TexturePacker",
                "--sheet", imageFile,
                "--texture-format", textureType,
                "--format", "cocos2d",
                "--data", plistFile,
                "--algorithm", "MaxRects",
                "--maxrects-heuristics", "Best",
                "--basic-sort-by", "Best",
                "--basic-order", "Ascending",
                "--max-size", "2048",
                "--size-constraints", "POT",
                "--force-squared",
                "--force-word-aligned",
                "--pack-mode", "Best",
                "--multipack",
                "--common-divisor-x", "4",
                "--common-divisor-y", "4",
                "--shape-padding", "2",
                "--border-padding", "2",
                "--enable-rotation",
                "--trim-mode", "None",
                # "--disable-clean-transparency",
                "--opt", textureFormat,
                "--pvr-quality", pvrQuality,
                # "--premultiply-alpha",
                "--png-opt-level", "0",
                "--extrude", "4",
                "--scale", scale,
                "--scale-mode", "Smooth",
                 workTopDir])
            """

            shutil.rmtree(workTopDir)
# ---
# main function
#
if __name__ == '__main__':
    sys.stdout = codecs.lookup('utf_8')[-1](sys.stdout)
    argv = sys.argv
    argc = len(argv)
    if argc == 3:
        makeAreaAtlas(argv[1], argv[2])
    else:
        print "python makeAreaAtlas.py {srcDir} {dstDir}"






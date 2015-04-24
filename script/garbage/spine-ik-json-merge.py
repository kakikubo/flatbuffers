#! /usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import codecs
import json
from collections import OrderedDict



# ---
# root function
#
def ikMerge(mainJson, subJson):
    with open(mainJson, 'r') as f:
        mainData = json.loads(f.read(), object_pairs_hook=OrderedDict)

    with open(subJson, 'r') as f:
        subData = json.loads(f.read(), object_pairs_hook=OrderedDict)

    ikBones = []
    ikData = mainData['ik']
    for ik in ikData:
        if ik.has_key('target'):
            ikBones.append(ik['target'])

    subDataKeys = subData.keys()
    for subDataKey in subDataKeys:
        if subDataKey == 'animations':
            subAnimations = subData[subDataKey]
            mainAnimations = mainData[subDataKey]
            if not mainData.has_key(subDataKey):
                print '{0} dont have keys [{1}]'.format(mainJson, subDataKey)
            subAnimKeys = subAnimations.keys()
            for subAnimKey in subAnimKeys:
                subAnim = subAnimations[subAnimKey]
                mainAnim = mainAnimations[subAnimKey]
                if not mainAnimations.has_key(subAnimKey):
                    print '{0}:{1} dont have key [{2}]'.format(mainJson, subDataKey, subAnimKey)
                subAnimAttbKeys = subAnim.keys()
                for subAnimAttbKey in subAnimAttbKeys:
                    if subAnimAttbKey == 'bones':
                        subBones = subAnim[subAnimAttbKey]
                        mainBones = mainAnim[subAnimAttbKey]
                        if not mainAnim.has_key(subAnimAttbKey):
                            print '{0}:{1}:{2} dont have key [{3}]'.format(mainJson, subDataKey, subAnimKey, subAnimAttbKey)
                        boneKeys = subBones.keys()
                        for boneKey in boneKeys:
                            mainBones[boneKey] = subBones[boneKey]
                        for ikBone in ikBones:
                            mainBoneKeys = mainBones.keys()
                            for mainBoneKey in mainBoneKeys:
                                if ikBone == mainBoneKey:
                                    del mainData[subDataKey][subAnimKey][subAnimAttbKey][mainBoneKey]
                                    #print 'del {0}:{1}:{2}:{3}'.format(subDataKey,subAnimKey,subAnimAttbKey,mainBoneKey)
    if mainData.has_key('animations'):
        animations = mainData['animations']
        animKeys = animations.keys()
        for animKey in animKeys:
            anim = animations[animKey]
            attbKeys = anim.keys()
            for attbKey in attbKeys:
                attb = anim[attbKey]
                if attbKey == 'ik':
                    del mainData['animations'][animKey][attbKey]
            if animKey == 'ik':
                del mainData['animations'][animKey]
    del mainData['ik']
    print json.dumps(mainData)



# ---
# default help message
#
def printHelp():
    print '''error: not enough args
    e.g. python spine-ik-json-merge.py main.json ik.json'''



# ---
# main function
#
if __name__ == '__main__':
    sys.stdout = codecs.lookup('utf_8')[-1](sys.stdout)
    argv = sys.argv
    argc = len(argv)
    if argc < 3:
        printHelp()
    else:
        ikMerge(argv[1],argv[2])

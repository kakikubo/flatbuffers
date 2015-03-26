#! /usr/bin/python
# -*- coding: utf-8 -*-

import sys
import codecs
import json
import datetime
from collections import OrderedDict

debugPrint = False
summarizeSameObject = False
listingRepeatedObjectAgain = False

tableDictDict = OrderedDict({})
sameDict = OrderedDict({})



# ---
# analyze list
#
def analyzeList(key, data):
    for value in data:
        if isinstance(value, dict):
            analyzeDict(key, value)
        else :
            print '### Warning!\nunexpected type in list. {0}\n###'.format(str(type(data)))



# ---
# update same named dictionary
#
def updateSameNamedDict(existDict, newDict):
    tableDict = OrderedDict({})

    # create list from dict
    existDictKeys = existDict.keys()
    existList = [existDict[existDictKey] for existDictKey in existDictKeys]
    newDictKeys = newDict.keys()
    newList = [newDict[newDictKey] for newDictKey in newDictKeys]

    if debugPrint:
        print 'before exist:' + str(existDict)
        print 'before new  :' + str(newDict)

    # align value type
    for existOne in existList:
        for newOne in newList:
            if existOne[0] == newOne[0] and existOne[1] == newOne[1]:
                if existOne[2] == 'float' or newOne[2] == 'float':
                    existOne[2] = 'float'
                    newOne[2] = 'float'
                elif existOne[2] == 'long' or newOne[2] == 'long':
                    existOne[2] = 'long'
                    newOne[2] = 'long'

    # add elements from existDict. (add element from newDict if same element found.)
    for existOne in existList:
        try:
            index = newList.index(existOne)
            for i in range(index+1):
                tableDict[newList[i][1]] = newList[i]
            del newList[0:index+1]
        except ValueError:
            tableDict[existOne[1]] = existOne

    # add remaining elements
    for newOne in newList:
        newKey = newOne[1]
        tableDict[newKey] = newOne

    if debugPrint:
        print 'after       :' + str(tableDict)

    return tableDict



# ---
# add new dict
#
def addTableDict(key, tableDict):
    # search existing dict
    dictKeys = tableDictDict.keys()
    for dictKey in dictKeys:
        if tableDictDict[dictKey] == tableDict:
            if summarizeSameObject:
                if key != dictKey:
                    sameDict[key] = dictKey
                return
            else:
                if key == dictKey:
                    return

    # add new dict
    if key in tableDictDict:
        tableDict = updateSameNamedDict(tableDictDict[key], tableDict)
    tableDictDict[key] = tableDict



# ---
# analyze dict
#
def analyzeDict(key, data):
    key = (key[0]).upper() + key[1:]
    tableDict = OrderedDict({})
    dataKeys = data.keys()
    for dataKey in dataKeys:
        dataData = data[dataKey]
        if isinstance(dataData, dict):
            analyzeDict(dataKey, dataData)
            lowerKey = (dataKey[0]).lower() + dataKey[1:]
            upperKey = (dataKey[0]).upper() + dataKey[1:]
            tableDict[dataKey] = ['dict', lowerKey, upperKey]
        elif isinstance(dataData, list):
            lowerKey = (dataKey[0]).lower() + dataKey[1:]
            upperKey = (dataKey[0]).upper() + dataKey[1:]
            analyzeList(dataKey, dataData)
            tableDict[dataKey] = ['list', lowerKey, upperKey]
        elif isinstance(dataData, long):
            tableDict[dataKey] = ['scalar', dataKey, 'long']
        elif isinstance(dataData, bool):
            tableDict[dataKey] = ['scalar', dataKey, 'bool']
        elif isinstance(dataData, int):
            tableDict[dataKey] = ['scalar', dataKey, 'int']
        elif isinstance(dataData, float):
            tableDict[dataKey] = ['scalar', dataKey, 'float']
        elif isinstance(dataData, unicode):
            tableDict[dataKey] = ['scalar', dataKey, 'string']
        else:
            tableDict[dataKey] = ['scalar', dataKey, str(type(dataData))]
    addTableDict(key, tableDict)



# ---
# return dict string for fbs format
#
def getOneDictString(key, tableDict):
    tableDictKeys = tableDict.keys()

    # retype same dict
    if summarizeSameObject:
        for tableDictKey in tableDictKeys:
            value = tableDict[tableDictKey]
            if sameDict.has_key(value[1]):
                value[2] = sameDict[value[1]]

    # re-list repeated dict/list/scalar
    if listingRepeatedObjectAgain:
        tableDictLen = len(tableDictKeys)
        newDict = OrderedDict({})
        i = 0
        while i < tableDictLen:
            now = tableDict[tableDictKeys[i]]
            count = i+1
            while count < tableDictLen:
                nextDict = tableDict[tableDictKeys[count]]
                if now[2] == nextDict[2]:
                    count += 1
                else:
                    break
            num  = count-i
            if num > 1:
                newDict[now[1]] = ['list', now[1], now[2]]
            else:
                newDict[now[1]] = now
            i += num

        # update
        tableDict = newDict

    tableStr = 'table {0} {{\n'.format(key)
    tableDictKeys = tableDict.keys()
    for tableDictKey in tableDictKeys:
        value = tableDict[tableDictKey]
        lid = value[0]
        lname = value[1]
        ltype = value[2]

        if lid == 'dict':
            tableStr += '\t{0}:{1};\n'.format(lname, ltype)
        elif lid == 'list':
            tableStr += '\t{0}:[{1}];\n'.format(lname, ltype)
        elif lid == 'scalar':
            tableStr += '\t{0}:{1};\n'.format(lname, ltype)
        else:
            tableStr += '\t{0}:{1};\n'.format(id, id)
    tableStr += '}\n'
    return tableStr



# ---
# output analyzed dicts as flatbuffers schema
#
def printDicts(rootName, nameSpace):
    d = datetime.datetime.today()
    print '// {0} : {1}\n'.format(d.strftime('%Y-%m-%d %H:%M:%S'), 'generated by json2fbs.py')

    # output namespace
    print 'namespace {0};\n'.format(nameSpace)

    # output tables
    keys = tableDictDict.keys()
    for key in keys:
        print getOneDictString(key, tableDictDict[key])

    # output root_type
    print 'root_type {0};'.format(rootName)

    if debugPrint:
        keys = sameDict.keys()
        for key in keys:
            print '{0}:{1}'.format(key, sameDict[key])



# ---
# root function
#
def json2fbs(jsonFile, rootName, nameSpace):
    with open(jsonFile, 'r') as f:
        jsonData = json.loads(f.read(), object_pairs_hook=OrderedDict)
        if isinstance(jsonData, dict):
            analyzeDict(rootName, jsonData)
            printDicts(rootName, nameSpace)
        else:
            print 'unsupported format. params:[{0}][{1}][{2}]'.format(jsonFile, rootName, nameSpace)



# ---
# default help message
#
def printHelp():
    print '''    need at least 2 args.
    [this] [json file] [root name] [add namespace (option)]
    e.g. python json2fbs.py master.json Master test.mytest'''



# ---
# main function
#
if __name__ == '__main__':
    sys.stdout = codecs.lookup('utf_8')[-1](sys.stdout)
    argv = sys.argv
    argc = len(argv)
    if argc < 3:
        printHelp()
    elif argc < 4:
        json2fbs(argv[1],argv[2],'')
    else:
        json2fbs(argv[1],argv[2],argv[3])

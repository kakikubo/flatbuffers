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

def addHideFlag(id):
    json_file = "./kms_master_asset/editor/areaInfo/areaInfo_" + id + ".json"
    with open(json_file, 'r') as f:
        master = json.loads(f.read(), object_pairs_hook=OrderedDict)
        id = 1
        for item in master["areaInfo_item"]["wall"]:
            item["hide"] = False
    with open(json_file, 'w') as f:
        j = json.dumps(master, ensure_ascii = False, indent = 4)
        f.write(j.encode("utf-8"))
# ---
# main function
#
if __name__ == '__main__':
    addHideFlag(sys.argv[1])
    exit(0)

#! /usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function
import os
import sys
import re
import argparse
import json
import logging
from logging import info, warning, error
from collections import OrderedDict
from glob import glob

def verify_user_json(src_dir):
    user_data = OrderedDict()
    for json_path in glob("%s/*.json" % src_dir):
        key = re.sub('.json$', '', os.path.basename(json_path))
        info("verify user data: %s" % key)
        with open(json_path, 'r') as f:
            user_data[key] = json.load(f, object_pairs_hook=OrderedDict)

    # TODO check user data

    return True

# ---
# main function
#
if __name__ == '__main__':
    logging.basicConfig(level = logging.INFO, format = '%(asctime)-15s %(levelname)s %(message)s')

    parser = argparse.ArgumentParser(description = 'verify user data json')
    parser.add_argument('input_dir', metavar = 'input.dir',  help = 'input user data json dir')
    args = parser.parse_args()

    info("input dir = %s" % args.input_dir)
    verify_user_json(args.input_dir)
    info("no error is detected")
    exit(0)

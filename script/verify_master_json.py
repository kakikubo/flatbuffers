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

def verify_master_json(src_schema, src_data):
    with open(src_schema, 'r') as f:
        master_schema = json.load(f, object_pairs_hook=OrderedDict)
    with open(src_data, 'r') as f:
        master_data = json.load(f, object_pairs_hook=OrderedDict)

    # TODO check master data

    return True

# ---
# main function
#
if __name__ == '__main__':
    logging.basicConfig(level = logging.INFO, format = '%(asctime)-15s %(levelname)s %(message)s')

    parser = argparse.ArgumentParser(description = 'verify master data json')
    parser.add_argument('input_schema', metavar = 'input.schema', help = 'input master data schema json file')
    parser.add_argument('input_data',   metavar = 'input.data',   help = 'input master data json file')
    args = parser.parse_args()

    info("input schema = %s" % args.input_schema)
    info("input data = %s" % args.input_data)
    verify_master_json(args.input_schema, args.input_data)
    info("no error is detected")
    exit(0)

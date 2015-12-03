#! /usr/bin/python
# -*- coding: utf-8 -*-

import argparse
import hashlib
import json
import os
import re
from collections import OrderedDict
import logging
from logging import info, warning, debug

class ManifestQueue():
    def __init__(self, dest_dir, remote_dir_manifests):
        self.dest_dir = dest_dir
        self.remote_dir_manifests = remote_dir_manifests

    def normalize(self, manifest_paths):
        # create file reference list from fist manifest
        manifests = []
        queue_assign_map = OrderedDict()
        for i, manifest_path in enumerate(manifest_paths):
            manifest = None
            with open(manifest_path, 'r') as f:
                manifest = json.load(f, object_pairs_hook=OrderedDict)
            info("input %d = %d: %s" % (i, len(manifest['assets']), manifest_path))
            manifests.append(manifest)
            for key, asset in manifest['assets'].iteritems():
                if not queue_assign_map.has_key(key):
                    queue_assign_map[key] = i
        debug(json.dumps(queue_assign_map, indent=2))

        # strip each manifest
        for i, manifest in enumerate(manifests):
            assets = OrderedDict()
            for key, asset in manifest['assets'].iteritems():
                if queue_assign_map[key] == i:
                    assets[key] = asset
            manifest['assets'] = assets
            info("output %d = %d" % (i, len(manifest['assets'])))

        # add all following manifests to first manifest
        for i, manifest_path in enumerate(manifest_paths[1:]):
            entry = os.path.join('manifests', os.path.basename(manifest_path))
            path  = os.path.join(self.remote_dir_manifests, os.path.basename(manifest_path))
            j     = json.dumps(manifests[i+1], indent=2)
            md5   = hashlib.md5(j).hexdigest()
            asset = OrderedDict([('md5', md5), ('path', path)])
            manifests[0]['assets'][entry] = asset

        # write all manifests
        for i, manifest_path in enumerate(manifest_paths):
            dest_path = os.path.join(self.dest_dir, os.path.basename(manifest_path))
            info("output %i: %s" % (i, dest_path))
            with open(dest_path, 'w') as f:
                json.dump(manifests[i], f, indent=2)
        return True

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='create and normalize manifest queue for AssetsManagaerEx', epilog="""\
example:
    $ ./manifest_queue.py project.manifest.1 project.manifest.2 project.manifest.3 project.manifest""")

    parser.add_argument('manifests', default = [], nargs='*', help='input manifests')
    parser.add_argument('--dest-dir', required=True, help = 'dest dir')
    parser.add_argument('--remote-dir', required=True, help = 'remote dir manifests')
    parser.add_argument('--log-level', help = 'log level (WARNING|INFO|DEBUG). default: INFO')
    args = parser.parse_args()
    logging.basicConfig(level = args.log_level or "INFO", format = '%(asctime)-15s %(levelname)s %(message)s')

    info("manifests: %s" % ', '.join(args.manifests))
    info("output dir: %s" % args.dest_dir)
    info("remote dir of manifests: %s" % args.remote_dir)
    queue = ManifestQueue(args.dest_dir, args.remote_dir)

    # project.manifest
    queue.normalize(args.manifests)

    exit(0)

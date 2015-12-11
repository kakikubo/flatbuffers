#! /usr/bin/python
# -*- coding: utf-8 -*-

import argparse
import hashlib
import json
import os
import re
from copy import copy
from collections import OrderedDict
import logging
from logging import info, warning, debug

class ManifestQueue():
    def __init__(self, project_dir, phase_dir, remote_dir_manifests, real_asset_dir):
        self.project_dir = project_dir
        self.phase_dir = phase_dir
        self.remote_dir_manifests = remote_dir_manifests
        self.real_asset_dir = real_asset_dir

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

        # add and write phase manifests
        for i, manifest_path in enumerate(manifest_paths):
            name, ext   = os.path.splitext(os.path.basename(manifest_path))
            dest_path   = os.path.join(self.phase_dir, 'phase.manifest'+ext)
            remote_path = os.path.join(self.remote_dir_manifests, 'phase.manifest'+ext)
            phase_manifest = copy(manifests[i])
            phase_manifest['assets'] = {}
            info("output %i: %s" % (i, dest_path))
            with open(dest_path, 'w') as f:
                json.dump(phase_manifest, f, indent=2)

            entry = os.path.join('manifests', os.path.basename(remote_path))
            j     = json.dumps(phase_manifest, indent=2)
            md5   = hashlib.md5(j).hexdigest()
            asset = OrderedDict([('md5', md5), ('path', remote_path)])
            manifests[0]['assets'][entry] = asset

        # write project.manifests
        total = 0;
        for i, manifest_path in enumerate(manifest_paths):
            dest_path = os.path.join(self.project_dir, os.path.basename(manifest_path))
            size = 0;
            if self.real_asset_dir:
                for key, asset in manifests[i]['assets'].iteritems():
                    path = os.path.join(self.real_asset_dir, key)
                    if os.path.exists(path):
                        size += os.path.getsize(path)
            info("output %i: %s (%dMB)" % (i, dest_path, size/1024/1024))
            with open(dest_path, 'w') as f:
                json.dump(manifests[i], f, indent=2)
            total += size

        if total > 0:
            info("total asset size = %dMB" % (total/1024/1024))
        return True

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='create and normalize manifest queue for AssetsManagaerEx', epilog="""\
example:
    $ ./manifest_queue.py project.manifest.1 project.manifest.2 project.manifest.3 project.manifest""")

    parser.add_argument('manifests', default = [], nargs='*', help='input manifests')
    parser.add_argument('--project-dir', required=True, help = 'output project.manifest dir')
    parser.add_argument('--phase-dir', required=True, help = 'output phase.manifest dir')
    parser.add_argument('--remote-dir', required=True, help = 'remote dir manifests')
    parser.add_argument('--asset-dir', required=True, help = 'real asset root path (to use calcurate data size)')
    parser.add_argument('--log-level', help = 'log level (WARNING|INFO|DEBUG). default: INFO')
    args = parser.parse_args()
    logging.basicConfig(level = args.log_level or "INFO", format = '%(asctime)-15s %(levelname)s %(message)s')

    info("manifests: %s" % ', '.join(args.manifests))
    info("output project.manifest dir: %s" % args.project_dir)
    info("output phase.manifest dir: %s" % args.phase_dir)
    info("remote dir of manifests: %s" % args.remote_dir)
    info("real asset root dir: %s" % args.asset_dir)
    queue = ManifestQueue(args.project_dir, args.phase_dir, args.remote_dir, args.asset_dir)

    # project.manifest
    queue.normalize(args.manifests)

    exit(0)

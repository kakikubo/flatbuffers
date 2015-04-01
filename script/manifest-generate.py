#! /usr/bin/python
# -*- coding: utf-8 -*-

import argparse
import hashlib
import json
import os

DEV_PACKAGE_URL = 'http://g-pc-4570.intra.gree-office.net:8080/asset/'
PRO_PACKAGE_URL = 'http://g-pc-4570.intra.gree-office.net:8080/asset/'

MANIFEST_FILE = 'project.manifest'
VERSION_FILE = 'version.manifest'

ENGINE_VERSION = 'Cocos2d-x v3.4'


def createAsstsWithMd5(root):
    if 0 < len(root) and root[len(root)-1] != '/':
      root = root+'/' # force root directory to end with '/'

    assetsDic = {}
    for assetsDir in [root]:
        for dpath, dnames, fnames in os.walk(assetsDir):
            for fname in fnames:
                if fname == MANIFEST_FILE or fname == VERSION_FILE:
                    continue

                path = os.path.join(dpath, fname)
                with open(path, 'r') as f:
                    byte = f.read()
                    assetPath = path[len(root):]
                    assetsDic[assetPath] = {'md5': hashlib.md5(byte).hexdigest()}
    return assetsDic

def createManifest(version, root, projectPath, versionPath, mode):
    manifest = {}

    if mode == 'dev':
        manifest['packageUrl'] = DEV_PACKAGE_URL
        manifest['remoteManifestUrl'] = DEV_PACKAGE_URL + MANIFEST_FILE
        manifest['remoteVersionUrl'] = DEV_PACKAGE_URL + VERSION_FILE
    else:
        manifest['packageUrl'] = PRO_PROJECT_URL
        manifest['remoteManifestUrl'] = PRO_PROJECT_URL + MANIFEST_FILE
        manifest['remoteVersionUrl'] =  PRO_PROJECT_URL + VERSION_FILE

    manifest['version'] = version
    manifest['engineVersion'] = ENGINE_VERSION

    with open(versionPath, 'w') as f:
        json.dump(manifest, f, sort_keys=True, indent=2)

    manifest['assets'] = {}
    manifest['assets'].update(createAsstsWithMd5(root))

    with open(projectPath, 'w') as f:
        json.dump(manifest, f, sort_keys=True, indent=2)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Generate asset manifest files for AssetsManagerEx', epilog="""\
example:
    $ ./manifest-generate.py 201504010000 bundled/preload/files bundled/preload/files/project.manifest bundled/preload/files/version.manifest""")
    parser.add_argument('version', metavar='version', help='manifest version string')
    parser.add_argument('root', metavar='root', help='root directory for asset files')
    parser.add_argument('project_manifest', metavar='project.manifest', help='output path for project.manifest')
    parser.add_argument('version_manifest', metavar='version.manifest', help='output path for version.manifest')
    parser.add_argument('--mode', default='dev', help='mode name (dev, production) default: dev')
    args = parser.parse_args()

    createManifest(args.version, args.root, args.project_manifest, args.version_manifest, args.mode)

#! /usr/bin/python
# -*- coding: utf-8 -*-

import argparse
import hashlib
import json
import os

BASE_URL = 'http://g-pc-4570.intra.gree-office.net:8080/'

MASTER_DIR = 'asset/'
PACKAGE_DIR = 'preload/'
MANIFEST_DIR = 'manifest/'
MANIFEST_FILE = 'project.manifest'
VERSION_FILE = 'version.manifest'

ENGINE_VERSION = 'Cocos2d-x v3.4'


def createAssetsWithMd5(root, base):
    if 0 < len(root) and not root.endswith('/'):
      root += '/' # force root directory to end with '/'

    assetsDic = {}
    for assetsDir in [root]:
        for dpath, dnames, fnames in os.walk(assetsDir):
            for fname in fnames:
                if fname == MANIFEST_FILE or fname == VERSION_FILE:
                    continue

                path = os.path.join(dpath, fname)
                with open(path, 'r') as f:
                    byte = f.read()
                    if byte == "": # AssetsManagerEx can not download size 0 file
                        if fname.endswith("_stringtable.txt"):
                            continue
                        else:
                            raise Exception, path+" is 0 size"

                    assetPath = path[len(root):]
                    asset = {}
                    asset['md5'] = hashlib.md5(byte).hexdigest()
                    asset['path'] = base + assetPath
                    assetsDic[assetPath] = asset
    return assetsDic

def createVersionManifest(dir, version):
    if 0 < len(dir) and not dir.endswith('/'):
        dir += '/' # force root directory to end with '/'

    manifest = {}
    
    manifest['packageUrl'] = BASE_URL
    manifest['remoteManifestUrl'] = BASE_URL + dir + MANIFEST_DIR + MANIFEST_FILE
    manifest['remoteVersionUrl'] = BASE_URL + dir + MANIFEST_DIR + VERSION_FILE
    
    manifest['version'] = version
    manifest['engineVersion'] = ENGINE_VERSION
    return manifest

def createManifest(version, root, projectPath, versionPath):
    manifest = createVersionManifest(MASTER_DIR, version)

    with open(versionPath, 'w') as f:
        json.dump(manifest, f, sort_keys=True, indent=2)

    manifest['assets'] = {}
    manifest['assets'].update(createAssetsWithMd5(root, MASTER_DIR))

    with open(projectPath, 'w') as f:
        json.dump(manifest, f, sort_keys=True, indent=2)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Generate asset manifest files for AssetsManagerEx', epilog="""\
example:
    $ ./manifest-generate.py ""master 201504010000"" asset/contents/ asset/dev/project.manifest asset/dev/version.manifest""")
    parser.add_argument('version', metavar='version', help='manifest version string')
    parser.add_argument('root', metavar='root', help='root directory for asset files')
    parser.add_argument('project_manifest', metavar='project.manifest', help='output path for project.manifest')
    parser.add_argument('version_manifest', metavar='version.manifest', help='output path for version.manifest')
    args = parser.parse_args()

    createManifest(args.version, args.root, args.project_manifest, args.version_manifest)

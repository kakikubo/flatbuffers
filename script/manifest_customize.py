#! /usr/bin/python
# -*- coding: utf-8 -*-

import argparse
import json
import os

import manifest_generate

def loadManifest(path):
    manifest = {}
    with open(path, 'r') as f:
        manifest = json.load(f)
    return manifest

def customizeManifest(version, root, dir_name, base_manifest, projectPath, versionPath):
    manifest = manifest_generate.createVersionManifest(dir_name, version)

    with open(versionPath, 'w') as f:
        json.dump(manifest, f, sort_keys=True, indent=2)

    assets = {}
    assets.update(manifest_generate.createAssetsWithMd5(root, dir_name))

    baseManifest = loadManifest(base_manifest)

    baseAssets = baseManifest.get('assets')
    for key in assets:
        asset = assets.get(key)
        if baseAssets.has_key(key):
            baseAsset = baseAssets.get(key)
            if baseAsset.get('md5') == asset.get('md5'):
                continue
        baseAssets[key] = asset
    manifest['assets'] = baseAssets

    with open(projectPath, 'w') as f:
        json.dump(manifest, f, sort_keys=True, indent=2)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Update asset manifest files for AssetsManagerEx', epilog="""\
    example:
    $ ./manifest_customize.py ""master 201504010000"" asset_USER_NAME/contents/ asset_USER_NAME asset/dev/project.manifest asset_USER_NAME/dev/project.manifest asset_USER_NAME/dev/version.manifest""")
    parser.add_argument('version', metavar='version', help='manifest version string')
    parser.add_argument('root', metavar='root', help='root directory for asset files')
    parser.add_argument('dir_name', metavar='dir_name', help='target directory name (e.g. v1.0, asset_masaru.ida, ...)')
    parser.add_argument('base_manifest', metavar='base_manifest', help='input manifest path')
    parser.add_argument('project_manifest', metavar='project.manifest', help='output path for project.manifest')
    parser.add_argument('version_manifest', metavar='version.manifest', help='output path for version.manifest')
    args = parser.parse_args()

    customizeManifest(args.version, args.root, args.dir_name, args.base_manifest, args.project_manifest, args.version_manifest)

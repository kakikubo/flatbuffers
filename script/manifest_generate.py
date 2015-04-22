#! /usr/bin/python
# -*- coding: utf-8 -*-

import urllib
import argparse
import hashlib
import json
import os

ENGINE_VERSION = 'Cocos2d-x v3.5'

def loadManifest(path):
    manifest = {}
    with open(path, 'r') as f:
        manifest = json.load(f)
    return manifest

def createAssetList(remote_dir, local_search_path):
    if 0 < len(local_search_path) and not local_search_path.endswith('/'):
       local_search_path += '/' # force local_search_path directory to end with '/'

    assetsDic = {}
    for dpath, dnames, fnames in os.walk(local_search_path):
        for fname in fnames:
            path = os.path.join(dpath, fname)
            with open(path, 'r') as f:
                byte = f.read()
                if byte == "": # AssetsManagerEx can not download size 0 file
                    if fname.endswith("_stringtable.txt"):
                        continue
                    else:
                        raise Exception, path+" is 0 size"

                assetPath = path[len(local_search_path):]
                asset = {}
                asset['md5'] = hashlib.md5(byte).hexdigest()
                asset['path'] = remote_dir + "/" + assetPath
                assetsDic[assetPath] = asset
    return assetsDic

def createVersionManifest(version, remote_manifest_url, remote_version_url, package_url):
    manifest = {}
    
    manifest['packageUrl'] = package_url
    manifest['remoteManifestUrl'] = remote_manifest_url
    manifest['remoteVersionUrl'] = remote_version_url
    
    manifest['version'] = version
    manifest['engineVersion'] = ENGINE_VERSION
    return manifest

def createManifest(dst_file_project_manifest, dst_file_version_manifest,
                   version, url_project_manifest, url_version_manifest, url_asset,
                   remote_dir_asset, local_asset_search_path, 
                   reference_manifest_path):

    manifest = createVersionManifest(version, url_project_manifest, url_version_manifest, url_asset)
    with open(dst_file_version_manifest, 'w') as f:
        json.dump(manifest, f, sort_keys=True, indent=2)

    assets = createAssetList(remote_dir_asset, local_asset_search_path)

    if reference_manifest_path == None or not os.path.exists(reference_manifest_path):
        manifest['assets'] = assets
    else:
        baseManifest = loadManifest(reference_manifest_path)

        baseAssets = baseManifest.get('assets')
        for key in assets:
            asset = assets.get(key)
            if baseAssets.has_key(key):
                baseAsset = baseAssets.get(key)
                if baseAsset.get('md5') == asset.get('md5'):
                    continue
            baseAssets[key] = asset
        manifest['assets'] = baseAssets

    for key in manifest['assets'].keys():
        manifest['assets'][key]['path'] = urllib.quote(manifest['assets'][key]['path'])

    for key in manifest['assets'].keys():
        if key == ".DS_Store" or key.endswith("/.DS_Store"):
            manifest['assets'].pop(key) 
    with open(dst_file_project_manifest, 'w') as f:
        json.dump(manifest, f, sort_keys=True, indent=2)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Generate asset manifest files for AssetsManagerEx', epilog="""\
example:
    $ ./manifest_generate.py  --ref reference.manifest project.manifest version.manifest ""version 1"" http://example.com/project.manifest http://exmaple.com/version.manifest http://exmaple.com/cdn ver1 asset""")

    parser.add_argument('dst_file_project_manifest', metavar='project.manifest', help='output path for project.manifest')
    parser.add_argument('dst_file_version_manifest', metavar='version.manifest', help='output path for version.manifest')

    parser.add_argument('version', metavar='version', help='manifest version string')
    parser.add_argument('url_project_manifest', metavar='url.project.manifest', help='url of project.manifest')
    parser.add_argument('url_version_manifest', metavar='url.version.manifest', help='url of version')
    parser.add_argument('url_asset', metavar='url.asset', help='base url for assets')
    parser.add_argument('remote_dir_asset', metavar='remote.dir.asset', help='remote directory for asset files')
    parser.add_argument('local_asset_search_path', metavar='local.asset.search.path', help='local asset path')
    parser.add_argument('--ref', metavar='reference.manifest.path', help='reference manifest path')
    args = parser.parse_args()

    createManifest(args.dst_file_project_manifest, args.dst_file_version_manifest,
        args.version, args.url_project_manifest, args.url_version_manifest, args.url_asset,
        args.remote_dir_asset, args.local_asset_search_path,
        args.ref)

#! /usr/bin/python
# -*- coding: utf-8 -*-

import urllib
import argparse
import hashlib
import json
import os
import re
from collections import OrderedDict
import logging
from logging import info, warning, debug
import fnmatch

ENGINE_VERSION = 'Cocos2d-x v3.5'

def loadManifest(path):
    manifest = {}
    with open(path, 'r') as f:
        manifest = json.load(f, object_pairs_hook=OrderedDict)
    return manifest

def createAssetList(remote_dir, local_search_path, filter_list, ext_list):
    if 0 < len(local_search_path) and not local_search_path.endswith('/'):
       local_search_path += '/' # force local_search_path directory to end with '/'
    local_search_path = os.path.normpath(local_search_path)

    walk_files = []
    for dpath, dnames, fnames in os.walk(local_search_path):
        for fname in fnames:
            walk_files.append(os.path.normpath(os.path.join(dpath, fname)))

    filtered_files = []
    if not filter_list:
        filtered_files = walk_files
    else:
        for l in filter_list:
            filtered_files += fnmatch.filter(walk_files, l)

    if ext_list:
        file_map = OrderedDict()
        for f in filtered_files:
            file_map[f] = True
        for f in file_map.keys():
            name, ext = os.path.splitext(f)
            if not ext[1:] in ext_list:
                continue
            for alter_ext in ext_list:
                prior_file = name + '.' + alter_ext
                if f == prior_file:
                    break
                elif prior_file in file_map:
                    del file_map[f]
        filtered_files = file_map.keys()

    assetsDic = OrderedDict()
    for path in filtered_files:
        with open(path, 'r') as f:
            byte = f.read()
            if byte == "": # AssetsManagerEx can not download size 0 file
                if fnmatch.fnmatch(path, "*stringtable.txt"):
                    continue
                else:
                    raise Exception("%s is empty file" % path)
            assetPath = path[len(local_search_path)+1:]
            asset = OrderedDict()
            asset['md5'] = hashlib.md5(byte).hexdigest()
            asset['path'] = remote_dir + "/" + assetPath
            assetsDic[assetPath] = asset
    return assetsDic

def filterByRefernceManifest(assets, reference_manifest_path, keep_ref_entries):
    if not os.path.exists(reference_manifest_path):
        raise Exception("reference manifest is not found: %s" % reference_manifest_path)
    baseManifest = loadManifest(reference_manifest_path)
    baseAssets = baseManifest.get('assets')
    if keep_ref_entries:
        for key in assets:
            #if not baseAssets.has_key(key):
            #    continue
            asset     = assets.get(key)
            baseAsset = baseAssets.get(key)
            if not baseAsset or baseAsset.get('md5') != asset.get('md5'):
                baseAssets[key] = asset
        assets = baseAssets
    else:
        for key in baseAssets:
            if not assets.has_key(key):
              continue
            asset     = assets.get(key)
            baseAsset = baseAssets.get(key)
            if baseAsset.get('md5') == asset.get('md5'):
                assets[key] = baseAsset
    return assets

def createVersionManifest(version, remote_manifest_url, remote_version_url, package_url):
    manifest = OrderedDict()
    
    manifest['packageUrl'] = package_url
    manifest['remoteManifestUrl'] = remote_manifest_url
    manifest['remoteVersionUrl'] = remote_version_url
    
    manifest['version'] = version
    manifest['engineVersion'] = ENGINE_VERSION
    return manifest

def loadFilterList(filter_fnmatch_path, local_asset_search_path):
    filter_list = ext_list = []
    with open(filter_fnmatch_path, 'r') as f:
        lines = f.readlines()
    for i, l in enumerate(lines):
        l = re.sub('#.*', '', l)
        l = re.sub('\s*D\s+.*', '', l) # ignore delete
        l = l.strip()
        if not l:
            continue
        m = re.match('\s*EXT\s+(.*)', l)
        if m: # extension
            if ext_list:
                raise Exception("extension list must appear just 1 line in filter file: %s" % l)
            ext_list = re.split('\s+', m.group(1))
        else: # file path
            if l[0] != '/':
                l = os.path.join(local_asset_search_path, l)
            filter_list.append(os.path.normpath(l))
    return (filter_list, ext_list)

def createManifest(dst_file_project_manifest, dst_file_version_manifest,
                   version, url_project_manifest, url_version_manifest, url_asset,
                   remote_dir_asset, local_asset_search_path, 
                   filter_fnmatch_path, reference_manifest_path, keep_ref_entries):

    manifest = createVersionManifest(version, url_project_manifest, url_version_manifest, url_asset)
    with open(dst_file_version_manifest, 'w') as f:
        json.dump(manifest, f, sort_keys=True, indent=2)

    filter_list = ext_list = None
    if filter_fnmatch_path:
        filter_list, ext_list = loadFilterList(filter_fnmatch_path, local_asset_search_path)
    assets = createAssetList(remote_dir_asset, local_asset_search_path, filter_list, ext_list)
    if reference_manifest_path:
        assets = filterByRefernceManifest(assets, reference_manifest_path, keep_ref_entries)
    manifest['assets'] = assets

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
    $ ./manifest_generate.py --ref reference.manifest --filer filter.list project.manifest version.manifest ""version 1"" http://example.com/project.manifest http://exmaple.com/version.manifest http://exmaple.com/cdn ver1 asset""")

    parser.add_argument('dst_file_project_manifest', metavar='project.manifest', help='output path for project.manifest')
    parser.add_argument('dst_file_version_manifest', metavar='version.manifest', help='output path for version.manifest')

    parser.add_argument('version', metavar='version', help='manifest version string')
    parser.add_argument('url_project_manifest', metavar='url.project.manifest', help='url of project.manifest')
    parser.add_argument('url_version_manifest', metavar='url.version.manifest', help='url of version')
    parser.add_argument('url_asset', metavar='url.asset', help='base url for assets')
    parser.add_argument('remote_dir_asset', metavar='remote.dir.asset', help='remote directory for asset files')
    parser.add_argument('local_asset_search_path', metavar='local.asset.search.path', help='local asset path')
    parser.add_argument('--filter', metavar='filter.fnmatch', help='asset filter list (fnmatch format)')
    parser.add_argument('--ref', metavar='reference.manifest.path', help='reference manifest path')
    parser.add_argument('--keep-ref-entries', default = False, action = 'store_true', help = 'do not delete entries only exists in reference manifest')
    parser.add_argument('--log-level', help = 'log level (WARNING|INFO|DEBUG). default: INFO')
    args = parser.parse_args()

    logging.basicConfig(level = args.log_level or "INFO", format = '%(asctime)-15s %(levelname)s %(message)s')

    createManifest(args.dst_file_project_manifest, args.dst_file_version_manifest,
        args.version, args.url_project_manifest, args.url_version_manifest, args.url_asset,
        args.remote_dir_asset, args.local_asset_search_path,
        args.filter, args.ref, args.keep_ref_entries)

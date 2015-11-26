#! /usr/bin/python
# -*- coding: utf-8 -*-

import urllib
import argparse
import hashlib
import json
import os
import re
import fnmatch
from collections import OrderedDict
import logging
from logging import info, warning, debug

ENGINE_VERSION = 'Cocos2d-x v3.8'

class ManifestGenerator():
    def __init__(self, version, url_project_manifest, url_version_manifest, url_asset,
                 remote_dir_asset, local_asset_search_path, 
                 filter_fnmatch_path, location_list_path, character_list_path, ui_list_path,
                 reference_manifest_path, keep_ref_entries):
        self.version = version
        self.url_project_manifest = url_project_manifest
        self.url_version_manifest = url_version_manifest
        self.url_asset = url_asset
        self.remote_dir_asset = remote_dir_asset
        self.local_asset_search_path = local_asset_search_path
        self.location_list_path = location_list_path
        self.character_list_path = character_list_path
        self.ui_list_path = ui_list_path
        self.filter_fnmatch_path = filter_fnmatch_path
        self.reference_manifest_path = reference_manifest_path
        self.keep_ref_entries = keep_ref_entries

        if 0 < len(self.local_asset_search_path) and not self.local_asset_search_path.endswith('/'):
            self.local_asset_search_path += '/' # force local_asset_search_path directory to end with '/'
        self.local_asset_search_path = os.path.normpath(self.local_asset_search_path)

    def load_manifest(self, path):
        manifest = {}
        with open(path, 'r') as f:
            manifest = json.load(f, object_pairs_hook=OrderedDict)
        return manifest

    def create_asset_list(self, remote_dir, filter_list, ext_list):
        walk_files = []
        for dpath, dnames, fnames in os.walk(self.local_asset_search_path):
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
                assetPath = path[len(self.local_asset_search_path)+1:]
                asset = OrderedDict()
                asset['md5'] = hashlib.md5(byte).hexdigest()
                asset['path'] = remote_dir + "/" + assetPath
                assetsDic[assetPath] = asset
        return assetsDic

    def filter_by_reference_manifest(self, assets, reference_manifest_path):
        if not os.path.exists(reference_manifest_path):
            raise Exception("reference manifest is not found: %s" % reference_manifest_path)
        baseManifest = self.load_manifest(reference_manifest_path)
        baseAssets = baseManifest.get('assets')
        if self.keep_ref_entries:
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

    def create_version_manifest(self):
        manifest = OrderedDict()
        manifest['packageUrl']        = self.url_asset
        manifest['remoteManifestUrl'] = self.url_project_manifest
        manifest['remoteVersionUrl']  = self.url_version_manifest
        manifest['version']           = self.version
        manifest['engineVersion']     = ENGINE_VERSION
        return manifest

    def load_filter_list(self, filter_fnmatch_path):
        debug("load filter list: %s", filter_fnmatch_path)
        filter_list = []
        ext_list = []
        location_list = []
        character_list = []
        ui_list = []
        with open(filter_fnmatch_path, 'r') as f:
            lines = f.readlines()
        for i, l in enumerate(lines):
            l = re.sub('#.*', '', l)
            l = re.sub('\s*D\s+.*', '', l) # ignore delete
            l = l.strip()
            if not l:
                continue
            m1 = re.match('^\s*EXT\s+(.*)', l)
            m2 = re.match('^\s*LOCATION\s+(.*)', l)
            m3 = re.match('^\s*CHRACTER\s+(.*)', l)
            m4 = re.match('^\s*UI\s+(.*)', l)
            m5 = re.match('^\s*INCLUDE\s+(.*)', l)
            if m1: # extension
                if ext_list:
                    raise Exception("extension list must appear just 1 line in filter file: %s" % l)
                ext_list = re.split('\s+', m1.group(1))
            elif m2: # location
                location_list += re.split('\s+', m2.group(1))
            elif m3: # character
                character_list += re.split('\s+', m3.group(1))
            elif m4: # ui
                ui_list += re.split('\s+', m4.group(1))
            elif m5: # include
                include_path = m5.group(1)
                if include_path[0] != '/':
                    include_path = os.path.join(os.path.dirname(filter_fnmatch_path), include_path)
                in_filter_list, in_ext_list, in_location_list, in_character_list, in_ui_list = self.load_filter_list(include_path)
                filter_list    += in_filter_list
                ext_list       += in_ext_list
                location_list  += in_location_list
                character_list += in_character_list
                ui_list        += in_ui_list
            else: # real file path
                for path in re.split('\s+', l):
                    if path[0] != '/':
                        path = os.path.join(self.local_asset_search_path, path)
                    filter_list.append(os.path.normpath(path))
        return (filter_list, ext_list, location_list, character_list, ui_list)

    def expand_filter_list(self, expand_list, expand_file):
        file_list = OrderedDict()
        with open(expand_file, 'r') as f:
            file_list = json.load(f, object_pairs_hook=OrderedDict)
        filter_list = []
        for expand_target in expand_list:
            filtered = fnmatch.filter(file_list.keys(), expand_target)
            for key in filtered:
                for l in file_list[key]:
                    if l[0] != '/':
                        l = l.replace('contents/', '') # FIXME
                        l = os.path.join(self.local_asset_search_path, l)
                    filter_list.append(os.path.normpath(l))
        return filter_list

    def create_project_manifest(self, version_manifest):
        manifest = version_manifest

        filter_list = ext_list = None
        if self.filter_fnmatch_path:
            filter_list, ext_list, location_list, character_list, ui_list = self.load_filter_list(self.filter_fnmatch_path)
        if filter_list and location_list and self.location_list_path:
            filter_list += self.expand_filter_list(location_list, self.location_list_path)
        if filter_list and character_list and self.character_list_path:
            filter_list += self.expand_filter_list(character_list, self.character_list_path)
        if filter_list and ui_list and self.ui_list_path:
            filter_list += self.expand_filter_list(ui_list, self.ui_list_path)
        debug("filter_list: "+json.dumps(filter_list, indent=2))

        assets = self.create_asset_list(self.remote_dir_asset, filter_list, ext_list)
        if self.reference_manifest_path:
            assets = generator.filter_by_reference_manifest(assets, self.reference_manifest_path)
        manifest['assets'] = assets

        for key in manifest['assets'].keys():
            manifest['assets'][key]['path'] = urllib.quote(manifest['assets'][key]['path'])

        for key in manifest['assets'].keys():
            if key == ".DS_Store" or key.endswith("/.DS_Store"):
                manifest['assets'].pop(key) 
        return manifest

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
    parser.add_argument('--location-list', metavar='location_file_list.json', help='character file list by id')
    parser.add_argument('--character-list', metavar='character_file_list.json', help='character file list by id')
    parser.add_argument('--ui-list', metavar='ui_file_list.json', help='ui file list by id')
    parser.add_argument('--ref', metavar='reference.manifest.path', help='reference project.manifest path')
    parser.add_argument('--keep-ref-entries', default = False, action = 'store_true', help = 'do not delete entries only exists in reference manifest')
    parser.add_argument('--log-level', help = 'log level (WARNING|INFO|DEBUG). default: INFO')
    args = parser.parse_args()

    logging.basicConfig(level = args.log_level or "INFO", format = '%(asctime)-15s %(levelname)s %(message)s')

    info("version = %s" % args.version)
    info("url project.manifest = %s" % args.url_project_manifest)
    info("url version.manifest = %s" % args.url_version_manifest)
    info("url asset = %s" % args.url_asset)
    info("remote dir asset = %s" % args.remote_dir_asset)
    info("local asset search path = %s" % args.local_asset_search_path)
    info("filter = %s" % args.filter)
    info("location list = %s" % args.location_list)
    info("character list = %s" % args.character_list)
    info("ui list = %s" % args.ui_list)
    info("ref = %s" % args.ref)
    info("keep_ref_entries = %s" % args.keep_ref_entries)
    generator = ManifestGenerator(args.version, args.url_project_manifest, args.url_version_manifest, 
            args.url_asset, args.remote_dir_asset, args.local_asset_search_path, 
            args.filter, args.location_list, args.character_list, args.ui_list, 
            args.ref, args.keep_ref_entries)

    # version.manifest
    version_manifest = generator.create_version_manifest()
    with open(args.dst_file_version_manifest, 'w') as f:
        json.dump(version_manifest, f, sort_keys=True, indent=2)
    debug(json.dumps(version_manifest, indent=2))

    # project.manifest
    project_manifest = generator.create_project_manifest(version_manifest)
    with open(args.dst_file_project_manifest, 'w') as f:
        json.dump(project_manifest, f, sort_keys=True, indent=2)
    debug(json.dumps(project_manifest, indent=2))

    exit(0)

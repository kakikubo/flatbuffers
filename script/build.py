#! /usr/bin/env python
# -*- coding: utf-8 -*-

from collections import OrderedDict
import os
import sys
import re
import codecs
import tempfile
import argparse
import json
import xlrd
import md5
import logging
import subprocess
from time import strftime
from subprocess import check_call, check_output, call, STDOUT
from shutil import move, rmtree, copy2, copytree
from glob import glob
from logging import info, warning, debug

class AssetBuilder():
    def __init__(self, command=None, target=None, asset_version=None, main_dir=None, master_dir=None, build_dir=None, mirror_dir=None, cdn_dir=None, git_dir=None):
        self.target            = target or 'master'
        self.is_master         = self.target == 'master'

        self.asset_version     = asset_version or target
        self.asset_version_dir = asset_version or target
        self.timestamp         = strftime('%Y-%m-%d %H:%M:%S')
        self_dir = os.path.dirname(os.path.abspath(__file__))

        # select main dir
        if command in ('debug', 'clean'):
            main_dir_list = [
                os.path.normpath(os.curdir+'/kms_'+target+'_asset')
            ]
        else: # build
            main_dir_list = [
                os.path.normpath(self_dir+'/../../box/kms_'+target+'_asset'),
                os.path.normpath(os.path.expanduser('~/Box Sync/kms_'+target+'_asset'))
            ]
        for main_dir_default in main_dir_list:
            if os.path.exists(main_dir_default):
                break
        self.org_main_dir = main_dir or main_dir_default
        if not os.path.exists(self.org_main_dir):
            raise Exception("main dir is not exists: %s" % self.org_main_dir)

        # select master dir
        if command in ('debug', 'clean'):
            master_dir_list = [
                os.path.normpath(os.curdir+'/kms_master_asset')
            ]
        elif target in ('hiroto.furuya'):
            master_dir_list = [
                git_dir,
                os.path.normpath(self_dir+'/../client/asset'),
                os.path.normpath(os.path.expanduser('~/kms/asset'))
            ]
        else:   # build standard
            master_dir_list = [
                os.path.normpath(self_dir+'/../../box/kms_master_asset'), \
                os.path.normpath(os.path.expanduser('~/Box Sync/kms_master_asset'))
            ]
        for master_dir_default in master_dir_list:
            if master_dir_default and os.path.exists(master_dir_default):
                break
        self.org_master_dir = master_dir or master_dir_default
        if not os.path.exists(self.org_master_dir):
            raise Exception("master dir is not exists: %s" % self.org_master_dir)

        # select build dir
        if command == 'build':
            #build_dir_default = tempfile.mkdtemp(prefix = 'kms_asset_builder_build_')
            #build_dir_default = os.curdir+'/.kms_asset_builder_build'
            build_dir_default  = os.path.expanduser('~')+'/kms_asset_builder_build/'+self.target
            mirror_dir_default = os.path.expanduser('~')+'/kms_asset_builder_mirror/'+self.target
        else: # debug clean
            build_dir_default  = os.curdir+'/.kms_asset_builder_build/'+self.target
            mirror_dir_default = build_dir_default
        self.build_dir  = build_dir or build_dir_default
        self.mirror_dir = mirror_dir or mirror_dir_default

        cdn_dir_default          = '/var/www/cdn'
        self.cdn_dir             = cdn_dir or cdn_dir_default
        self.git_dir             = git_dir
        self.main_dir            = self.mirror_dir+'/main'
        self.master_dir          = self.mirror_dir+'/master'
        self.remote_dir_asset    = self.asset_version_dir+'/contents' if self.is_master else self.target + '/contents'

        for dir in (self.build_dir, self.mirror_dir) :
            if not os.path.exists(dir):
                os.makedirs(dir)
        # isolate from modefation via box
        self.prepare_dir(self.org_main_dir, self.main_dir)
        if self.org_main_dir == self.org_master_dir:
            self.master_dir = self.main_dir
        else:
            self.prepare_dir(self.org_master_dir, self.master_dir)
        
        info("target = %s", self.target)
        info("asset version = '%s'", self.asset_version)
        info("main-dir = %s", self.org_main_dir)
        info("master-dir = %s", self.org_master_dir)
        info("build-dir = %s", self.build_dir)
        info("mirror-dir = %s", self.mirror_dir)
        info("cdn-dir = %s", self.cdn_dir)
        info("git-dir = %s", self.git_dir)
        info("remote-dir-asset = %s", self.remote_dir_asset)

        self.manifest_dir           = self.main_dir+'/manifests'
        self.master_schema_dir      = self.main_dir+'/master_derivatives'
        self.master_data_dir        = self.main_dir+'/master_derivatives'
        self.master_fbs_dir         = self.main_dir+'/master_derivatives'
        self.master_bin_dir         = self.main_dir+'/contents/master'
        self.manifest_phase_dir     = self.main_dir+'/contents/manifests'
        self.master_header_dir      = self.main_dir+'/master_header'
        self.user_class_dir         = self.main_dir+'/user_header'
        self.user_schema_dir        = self.main_dir+'/user_derivatives'
        self.user_header_dir        = self.main_dir+'/user_header'
        self.files_dir              = self.main_dir+'/contents/files'
        self.user_data_dir          = self.main_dir+'/user_data'
        self.spine_dir              = self.main_dir+'/contents/files/spine'
        self.font_dir               = self.main_dir+'/contents/files/font'
        self.weapon_dir             = self.main_dir+'/contents/files/weapon'
        self.files_ui_dir           = self.main_dir+'/contents/files/ui'
        self.area_texture_dir       = self.main_dir+'/area'
        self.ui_dir                 = self.main_dir+'/ui'
        self.texturepacker_dir      = self.main_dir+'/texturepacker'
        self.imesta_dir             = self.main_dir+'/imesta'
        self.distribution_dir       = self.main_dir+'/distribution'
        self.webview_dir            = self.main_dir+'/webview'

        self.org_manifest_dir       = self.org_main_dir+'/manifests'
        self.org_master_schema_dir  = self.org_main_dir+'/master_derivatives'
        self.org_master_data_dir    = self.org_main_dir+'/master_derivatives'
        self.org_master_fbs_dir     = self.org_main_dir+'/master_derivatives'
        self.org_master_bin_dir     = self.org_main_dir+'/contents/master'
        self.org_manifest_phase_dir = self.org_main_dir+'/contents/manifests'
        self.org_master_header_dir  = self.org_main_dir+'/master_header'
        self.org_user_class_dir     = self.org_main_dir+'/user_header'
        self.org_user_schema_dir    = self.org_main_dir+'/user_derivatives'
        self.org_user_header_dir    = self.org_main_dir+'/user_header'
        self.org_files_dir          = self.org_main_dir+'/contents/files'
        self.org_user_data_dir      = self.org_main_dir+'/user_data'
        self.org_spine_dir          = self.org_main_dir+'/contents/files/spine'
        self.org_font_dir           = self.org_main_dir+'/contents/files/font'
        self.org_weapon_dir         = self.org_main_dir+'/contents/files/weapon'
        self.org_files_ui_dir       = self.org_main_dir+'/contents/files/ui'
        self.org_area_texture_dir   = self.org_main_dir+'/area'
        self.org_ui_dir             = self.org_main_dir+'/ui'
        self.org_texturepacker_dir  = self.org_main_dir+'/texturepacker'
        self.org_imesta_dir         = self.org_main_dir+'/imesta'
        self.org_distribution_dir   = self.org_main_dir+'/distribution'
        self.org_webview_dir        = self.org_main_dir+'/webview'

        self.main_xlsx_dir            = self.main_dir+'/master'
        self.main_editor_dir          = self.main_dir+'/editor'
        self.main_editor_schema_dir   = self.main_dir+'/editor_schema'
        self.main_schema_dir          = self.main_dir+'/user'
        self.main_files_dir           = self.main_dir+'/files'
        #self.main_gd_dir              = self.main_dir+'/glyph_designer/'

        self.master_manifest_dir      = self.master_dir+"/manifests"
        self.master_xlsx_dir          = self.master_dir+'/master'
        self.master_editor_dir        = self.master_dir+'/editor'
        self.master_editor_schema_dir = self.master_dir+'/editor_schema'
        self.master_gd_dir            = self.master_dir+'/glyph_designer'
        self.master_user_schema_dir   = self.master_dir+'/user_derivatives'
        self.master_user_data_dir     = self.master_dir+'/user_data'
        self.master_distribution_dir  = self.master_dir+"/distribution"

        self.manifest_generate_bin  = self_dir+'/manifest_generate.py'
        self.manifest_queue_bin     = self_dir+'/manifest_queue.py'
        self.xls2json_bin           = self_dir+'/master_data_xls2json.py'
        self.json2fbs_bin           = self_dir+'/json2fbs.py'
        self.json2macro_bin         = self_dir+'/json2macro.py'
        self.flatc_bin              = self_dir+'/flatc'
        self.fbs2class_bin          = self_dir+'/fbs2class.py'
        self.json2font_bin          = self_dir+'/json2font.py'
        self.merge_editor_json_bin  = self_dir+'/merge_editor_json.py'
        self.sort_master_json_bin   = self_dir+'/sort-master-json.py'
        self.verify_master_json_bin = self_dir+'/verify_master_json.py'
        self.strip_master_json_bin  = self_dir+'/strip_master_json.py'
        self.delete_element_bin     = self_dir+'/delete-element.py'
        self.make_weapon_atlas_bin  = self_dir+'/make_weapon_atlas.py'
        self.make_ui_atlas_bin      = self_dir+'/make_ui_atlas.py'
        self.make_area_atlas_bin    = self_dir+'/make_area_atlas.py'
        self.update_webviews_bin    = self_dir+'/update_webviews.py'
        
        self.PROJECT_MANIFEST_FILE          = 'project.manifest'
        self.VERSION_MANIFEST_FILE          = 'version.manifest'
        self.PHASE_MANIFEST_FILE            = 'phase.manifest'
        self.REFERENCE_MANIFEST_FILE        = 'dev.reference.manifest'
        self.ASSET_LIST_FILE                = 'dev.asset_list.json'
        self.MASTER_JSON_SCHEMA_FILE        = 'master_schema.json'
        self.MASTER_JSON_DATA_FILE          = 'master_data.json'
        self.MASTER_BUNDLED_JSON_DATA_FILE  = 'master_data_bundled.json'
        self.MASTER_BUNDLED_KEYS_FILE       = 'master_data_bundled_keys.json'
        self.MASTER_MACRO_FILE              = 'MasterAccessors.h'
        self.MASTER_FBS_FILE                = 'master_data.fbs'
        self.MASTER_BIN_FILE                = 'master_data.bin'
        self.MASTER_BUNDLED_BIN_FILE        = 'master_data_bundled.bin'
        self.MASTER_HEADER_FILE             = 'master_data_generated.h'
        self.MASTER_MD5_FILE                = 'master_data_generated_md5.h'
        self.MASTER_MD5_DEFINE              = 'KMS_MASTER_DATA_VERSION'
        self.EDITOR_MASTER_JSON_SCHEMA_FILE = 'editor_master_schema.json'
        self.EDITOR_MASTER_JSON_DATA_FILE   = 'editor_master_data.json'
        self.EDITOR_MASTER_MACRO_FILE       = 'EditorMasterAccessors.h'
        self.EDITOR_MASTER_FBS_FILE         = 'editor_master_data.fbs'
        self.EDITOR_MASTER_BIN_FILE         = 'editor_master_data.bin'
        self.EDITOR_MASTER_HEADER_FILE      = 'editor_master_data_generated.h'
        self.EDITOR_MASTER_MD5_FILE         = 'editor_master_data_generated_md5.h'
        self.EDITOR_MASTER_MD5_DEFINE       = 'KMS_MASTER_DATA_VERSION'
        self.MASTER_FBS_ROOT_NAME           = 'MasterDataFBS'
        self.MASTER_FBS_NAMESPACE           = 'kms.masterdata'
        self.USER_FBS_FILE                  = 'user_data.fbs'
        self.USER_CLASS_FILE                = 'user_data.h'
        self.USER_MD5_FILE                  = 'user_data_md5.h'
        self.USER_MD5_DEFINE                = 'KMS_USER_DATA_VERSION'
        self.USER_JSON_SCHEMA_FILE          = 'user_schema.json'
        self.USER_JSON_DATA_FILE            = 'default.json'
        self.USER_HEADER_FILE               = 'user_data_generated.h'
        self.USER_FBS_ROOT_NAME             = 'UserDataFBS'
        self.USER_FBS_NAMESPACE             = 'kms.userdata'
        self.LOCATION_FILE_LIST             = 'location_file_list.json'
        self.CHARACTER_FILE_LIST            = 'character_file_list.json'
        self.UI_FILE_LIST                   = 'ui_file_list.json'
        self.DEV_CDN_URL                    = 'http://kms-dev.dev.gree.jp/cdn'
        self.S3_CDN_URL                     = 'https://s3-ap-northeast-1.amazonaws.com/gree-kms-assets'
        self.S3_INTERNAL_URL                = 's3://gree-kms-assets'
        self.S3_CREDENTIALS_FILE            = '~/.aws/credentials'
        self.MASTER_DATA_ROW_START          = 3

    # prepare and isolate source data via box
    def prepare_dir(self, src, dest):
        for root, dirnames, filenames, in os.walk(src):
            for dir in dirnames:
                if re.search('[^\w\.-]', dir):
                    raise Exception("invalid dirname is detected: "+root+'/'+dir)
            for file in filenames:
                if re.search('[^\w\.-]', file):
                    raise Exception("invalid filename is detected: "+root+'/'+file)

        if src[-1] != '/':
            src += '/'
        info("copytree '%s' -> '%s'" % (src, dest))
        cmdline = ['rsync', '-ac', '--exclude', '.DS_Store', '--exclude', '.git', '--delete', src, dest]
        info(' '.join(cmdline))
        check_call(cmdline)

    # setup dest directories
    def setup_dir(self):
        for path in (\
            self.build_dir, \
            self.main_files_dir, \
            self.manifest_dir, \
            self.master_editor_dir, \
            self.main_editor_dir, \
            self.master_xlsx_dir, \
            self.main_xlsx_dir, \
            self.master_schema_dir, \
            self.master_data_dir, \
            self.master_fbs_dir, \
            self.master_bin_dir, \
            self.master_header_dir, \
            self.user_header_dir, \
            self.user_class_dir):
            if not os.path.exists(path):
                os.makedirs(path)

    # get xlsx master data files
    def _get_xlsxes(self):
        xlsx_dirs = (self.master_xlsx_dir, self.main_xlsx_dir)
        xlsxes = {}
        for xlsx_dir in xlsx_dirs:
            for xlsx_path in glob("%s/*.xlsx" % xlsx_dir):
                basename = os.path.basename(xlsx_path)
                if re.match('^~\$', basename):
                    continue
                xlsxes[basename] = xlsx_path
        return xlsxes.values()

    def _get_xlsx_sheets(self, xlsx_path):
        sheets = []
        xlsx_book = xlrd.open_workbook(xlsx_path)
        for sheet in xlsx_book.sheets():
            sheets.append(sheet.name)
        return sheets

    # select file to exist
    def _get_exist_file(self, file_list):
        for file in file_list:
            if file and os.path.exists(file):
                return file
        raise Exception("cannot find existing file" % ', '.join(file_list))

    def _write_md5(self, src, dest, define):
        content = None
        with open(src, 'r') as f:
            content = f.read()
        hexdigest = md5.new(content).hexdigest()
        with open(dest, 'w') as f:
            f.write('#pragma once\n#define %s "%s"\n' % (define, hexdigest))
            return True
        return False

    # cerate master data json from xlsx
    def build_master_json(self, src_xlsxes=None, dest_schema=None, dest_data=None, except_json=False):
        src_xlsxes  = src_xlsxes  or self._get_xlsxes()
        dest_schema = dest_schema or self.build_dir+'/'+self.MASTER_JSON_SCHEMA_FILE
        dest_data   = dest_data   or self.build_dir+'/'+self.MASTER_JSON_DATA_FILE
        info("build master json: %s + %s" % (os.path.basename(dest_schema), os.path.basename(dest_data)))

        cmdline = [self.xls2json_bin] + src_xlsxes + ['--schema-json', dest_schema, '--data-json', dest_data]
        if except_json:
            cmdline.append('--except-json') 
        info(' '.join(cmdline))
        check_call(cmdline)
        return True

    # merge data of excel master and one of editor master 
    def merge_editor_schema(self, master_schema_json=None, editor_schema_json=None):
        master_schema_json = master_schema_json or self.build_dir+'/'+self.MASTER_JSON_SCHEMA_FILE
        main_editor_schema = self.main_editor_schema_dir+'/editor_schema.json'
        editor_schema_default = main_editor_schema if os.path.exists(main_editor_schema) else self.master_editor_schema_dir+'/editor_schema.json'
        editor_schema_json = editor_schema_json or editor_schema_default

        cmdline = [self.merge_editor_json_bin, master_schema_json, editor_schema_json]
        info(' '.join(cmdline))
        check_call(cmdline)
        return True

    # merge schema of excel master and one of editor master 
    def merge_editor_data(self, master_data_json=None, editor_dirs=None):
        master_data_json = master_data_json or self.build_dir+'/'+self.MASTER_JSON_DATA_FILE
        editor_dirs = editor_dirs or (self.master_editor_dir, self.main_editor_dir)
        editor_files = {}
        for editor_dir in editor_dirs:
            for dirpath, dirnames, filenames in os.walk(editor_dir):
                for filename in filenames:
                    base, ext = os.path.splitext(filename)
                    if ext != ".json":
                        continue
                    editor_path = os.path.join(dirpath, filename)
                    basename = os.path.basename(editor_path)
                    editor_files[basename] = editor_path

        cmdline = [self.merge_editor_json_bin, master_data_json] + editor_files.values()
        info(' '.join(cmdline))
        check_call(cmdline)

    # sort master json
    def sort_master_json(self, src_schema=None, src_data=None):
        src_schema = src_schema or self.build_dir+'/'+self.MASTER_JSON_SCHEMA_FILE
        src_data   = src_data or self.build_dir+'/'+self.MASTER_JSON_DATA_FILE
        info("sort master json: %s + %s" % (os.path.basename(src_schema), os.path.basename(src_data)))

        cmdline = [self.sort_master_json_bin, src_schema, src_data, src_data]
        info(' '.join(cmdline))
        check_call(cmdline)
        return True

    # check master data + user data + asset
    def verify_master_json(self, src_schema=None, src_data=None, asset_dirs=None, src_user_schema=None, src_user_data=None, dest_dir=None, verify_file_reference=False):
        src_schema      = src_schema or self.build_dir+'/'+self.MASTER_JSON_SCHEMA_FILE
        src_data        = src_data or self.build_dir+'/'+self.MASTER_JSON_DATA_FILE
        src_user_schema = self._get_exist_file((src_user_schema, self.build_dir+'/'+self.USER_JSON_SCHEMA_FILE, self.master_user_schema_dir+'/'+self.USER_JSON_SCHEMA_FILE)) if src_user_schema != False else False
        src_user_data   = self._get_exist_file((src_user_data, self.user_data_dir+'/'+self.USER_JSON_DATA_FILE, self.master_user_data_dir+'/'+self.USER_JSON_DATA_FILE)) if src_user_data != False else False
        asset_dirs      = asset_dirs or [self.org_main_dir, self.org_master_dir]
        dest_dir        = dest_dir or self.build_dir
        info("verify master data: %s + %s" % (os.path.basename(src_schema), os.path.basename(src_data)))

        opt_verify_file_reference = ['--verify-file-reference']        if verify_file_reference else []
        opt_user_schema           = ['--user-schema', src_user_schema] if src_user_schema else []
        opt_user_data             = ['--user-data', src_user_data]     if src_user_data else []

        cmdline = [self.verify_master_json_bin, src_schema, src_data, '--file-reference-list', dest_dir, '--asset-dir'] + asset_dirs + opt_user_schema + opt_user_data + opt_verify_file_reference
        info(' '.join(cmdline))
        check_call(cmdline)
        return True

    # create fbs from json
    def build_master_fbs(self, src_json=None, dest_fbs=None, root_name=None, namespace=None):
        src_json   = src_json  or self.build_dir+'/'+self.MASTER_JSON_SCHEMA_FILE
        dest_fbs   = dest_fbs  or self.build_dir+'/'+self.MASTER_FBS_FILE
        root_name  = root_name or self.MASTER_FBS_ROOT_NAME
        namespace  = namespace or self.MASTER_FBS_NAMESPACE
        info("build master fbs: %s" % os.path.basename(dest_fbs))

        cmdline = [self.json2fbs_bin, src_json, dest_fbs, '--root-name', root_name, '--namespace', namespace]
        info(' '.join(cmdline))
        check_call(cmdline)
        return True

    # create macro from json
    def build_master_macro(self, src_json=None, dest_macro=None):
        src_json   = src_json   or self.build_dir+'/'+self.MASTER_JSON_SCHEMA_FILE
        dest_macro = dest_macro or self.build_dir+'/'+self.MASTER_MACRO_FILE
        info("build master macro: %s" % os.path.basename(dest_macro))

        cmdline = [self.json2macro_bin, src_json, dest_macro]
        info(' '.join(cmdline))
        check_call(cmdline)
        return True

    # create bin+header from json+fbs
    def build_master_bin(self, src_json=None, src_fbs=None, dest_bin=None, dest_header=None, dest_md5=None, dest_define=None):
        src_json    = src_json    or self.build_dir+'/'+self.MASTER_JSON_DATA_FILE
        src_fbs     = src_fbs     or self.build_dir+'/'+self.MASTER_FBS_FILE
        dest_bin    = dest_bin    or self.build_dir+'/'+self.MASTER_BIN_FILE
        dest_header = dest_header or self.build_dir+'/'+self.MASTER_HEADER_FILE
        dest_md5    = dest_md5    or self.build_dir+'/'+self.MASTER_MD5_FILE
        dest_define = dest_define or self.MASTER_MD5_DEFINE
        dest_dir    = os.path.dirname(dest_bin)
        info("build master bin: %s + %s" % (os.path.basename(dest_bin), os.path.basename(dest_header)))
        if os.path.dirname(dest_bin) != os.path.dirname(dest_header):
            raise Exception("%s and %s must be same dir" % (dest_bin, dest_header))

        cmdline = [self.flatc_bin, '-c', '-b', '-o', dest_dir, src_fbs, src_json]
        info(' '.join(cmdline))
        check_call(cmdline)

        return self._write_md5(dest_header, dest_md5, dest_define)

    def build_master_bundled_bin(self, src_json=None, src_fbs=None, src_bundled_keys=None, dest_bundled_json=None, dest_bundled_bin=None):
        src_json          = src_json          or self.build_dir+'/'+self.MASTER_JSON_DATA_FILE
        src_fbs           = src_fbs           or self.build_dir+'/'+self.MASTER_FBS_FILE
        src_bundled_keys  = src_bundled_keys  or self.distribution_dir+'/'+self.MASTER_BUNDLED_KEYS_FILE
        dest_bundled_json = dest_bundled_json or self.build_dir+'/'+self.MASTER_BUNDLED_JSON_DATA_FILE
        dest_bundled_bin  = dest_bundled_bin  or self.build_dir+'/'+self.MASTER_BUNDLED_BIN_FILE
        dest_dir          = os.path.dirname(dest_bundled_bin)

        if not os.path.exists(src_bundled_keys):
            info("skip build master bundled")
            return True

        info("build master bundled json + bin: %s + %s" % (os.path.basename(dest_bundled_json), os.path.basename(dest_bundled_bin)))

        cmdline = [self.strip_master_json_bin, src_json, dest_bundled_json, src_bundled_keys]
        info(' '.join(cmdline))
        check_call(cmdline)

        cmdline = [self.flatc_bin, '-b', '-o', dest_dir, src_fbs, dest_bundled_json]
        info(' '.join(cmdline))
        check_call(cmdline)

        return True

    # strip spine character animations
    def build_spine(self, src_xlsxes=None, src_spine_dir=None, dest_dir=None):
        src_xlsxes    = src_xlsxes    or self._get_xlsxes()
        src_spine_dir = src_spine_dir or self.spine_dir
        dest_dir      = dest_dir      or self.build_dir

        config = [
            #['characterSpine', '300:550'],
            #['npcSpine',       '450:550'],
            #['snpcSpine',      '350:550']
            ['characterSpine', '0:2000'],
            ['npcSpine',       '0:2000'],
            ['snpcSpine',      '0:2000']
        ]
        for xlsx in self._get_xlsxes():
            sheets = self._get_xlsx_sheets(xlsx)
            for conf in config:
                sheet_name = conf[0]
                size_limit = conf[1]
                if not sheet_name in sheets:
                    continue
                spine_file     = re.sub('Spine$', '.json', sheet_name)
                src_spine_json = src_spine_dir+'/'+sheet_name+'/'+spine_file
                dest_spine_dir = dest_dir+'/'+sheet_name
                if not os.path.exists(src_spine_json):
                    continue
                if not os.path.exists(dest_spine_dir):
                    os.makedirs(dest_spine_dir)

                info("build spine: %s:%s %s" % (os.path.basename(xlsx), sheet_name, os.path.basename(src_spine_json)))
                cmdline = [self.delete_element_bin, xlsx, sheet_name, str(self.MASTER_DATA_ROW_START), "hasTwinTail", src_spine_json, dest_spine_dir, '--size-limit', size_limit]
                info(' '.join(cmdline))
                check_call(cmdline)
        return True

    # create weapon atlas from json
    def build_weapon(self, src_xlsxes=None, src_weapon_dir=None, dest_dir=None, dummy_png=None):
        src_xlsxes     = src_xlsxes     or self._get_xlsxes()
        src_weapon_dir = src_weapon_dir or self.weapon_dir
        dest_dir       = dest_dir       or self.build_dir
        dummy_png      = dummy_png      or os.path.join(self.weapon_dir, 'dummy.png')

        if not os.path.exists(src_weapon_dir):
            return True

        for xlsx in self._get_xlsxes():
            sheets = self._get_xlsx_sheets(xlsx)
            for sheet in sheets:
                if sheet == "weaponPosition":
                    dest_weapon_dir = dest_dir+'/'+"weapon"
                    if not os.path.exists(dest_weapon_dir):
                        os.makedirs(dest_weapon_dir)

                    info("build weapon atlas: %s:" % os.path.basename(xlsx))
                    cmdline = [self.make_weapon_atlas_bin, xlsx, "weaponPosition", str(self.MASTER_DATA_ROW_START), "positionX", dest_weapon_dir, '--complete-png', dummy_png, '--src-dir', src_weapon_dir]
                    info(' '.join(cmdline))
                    check_call(cmdline)
        return True

    # create ui texture atlas by texture packer
    def build_ui_atlas(self, src_dir=None, dest_dir=None, work_dir=None):
        src_dir  = src_dir  or self.ui_dir
        dest_dir = dest_dir or self.build_dir+'/ui'
        work_dir = work_dir or self.build_dir+'/ui_work'

        if not os.path.exists(src_dir):
            return True

        info("build ui texture atlas: %s:" % src_dir)
        cmdline = [self.make_ui_atlas_bin, src_dir, dest_dir, '--work-dir', work_dir, '--verify-filename']
        info(' '.join(cmdline))
        check_call(cmdline)
        return True

    # create ui texture atlas by texture packer
    def build_area_atlas(self, src_dir=None, dest_dir=None, work_dir=None):
        src_dir  = src_dir  or self.area_texture_dir
        dest_dir = dest_dir or self.build_dir+'/areaAtlas'
        work_dir = work_dir or self.build_dir+'/area_work'

        if not os.path.exists(src_dir):
            return True

        info("build area texture atlas: %s:" % src_dir)
        cmdline = [self.make_area_atlas_bin, src_dir, dest_dir, '--work-dir', work_dir, '--verify-filename']
        info(' '.join(cmdline))
        check_call(cmdline)
        return True

    # create class header from fbs
    def build_user_class(self, src_fbs=None, dest_class=None, dest_schema=None, dest_md5=None, dest_define=None, namespace=None):
        src_fbs     = src_fbs     or self.main_schema_dir+'/'+self.USER_FBS_FILE
        dest_class  = dest_class  or self.build_dir+'/'+self.USER_CLASS_FILE
        dest_schema = dest_schema or self.build_dir+'/'+self.USER_JSON_SCHEMA_FILE
        dest_md5    = dest_md5    or self.build_dir+'/'+self.USER_MD5_FILE
        dest_define = dest_define or self.USER_MD5_DEFINE
        namespace   = namespace   or self.USER_FBS_NAMESPACE
        if not os.path.exists(src_fbs):
            return False

        info("build user class: %s + %s" % (os.path.basename(dest_class), os.path.basename(dest_schema)))
        cmdline = [self.fbs2class_bin, src_fbs, dest_class, dest_schema, '--namespace', namespace]
        info(' '.join(cmdline))
        check_call(cmdline)

        return self._write_md5(dest_class, dest_md5, dest_define)

    # create bin+header from json+fbs
    def build_user_header(self, src_json=None, src_fbs=None, dest_bin=None, dest_header=None):
        src_fbs     = src_fbs     or self.main_schema_dir+'/'+self.USER_FBS_FILE
        dest_header = dest_header or self.build_dir+'/'+self.USER_HEADER_FILE
        dest_dir    = os.path.dirname(dest_header)
        info("build user header: %s" % os.path.basename(dest_header))

        cmdline = [self.flatc_bin, '-c', '-o', dest_dir, src_fbs]
        info(' '.join(cmdline))
        check_call(cmdline)
        return True

    # create fnt+png from json
    def build_font(self, src_json=None, src_gd_dir=None, dest_font_dir=None):
        # build font by GDCL
        src_json      = src_json      or self.build_dir+'/'+self.MASTER_JSON_DATA_FILE
        src_gd_dir    = src_gd_dir    or self.master_gd_dir
        dest_font_dir = dest_font_dir or self.build_dir
        cmdline = [self.json2font_bin, src_json, src_gd_dir, dest_font_dir]
        info(' '.join(cmdline))
        check_call(cmdline)
        return True

    # copy all generated files 
    def install_list(self, list, build_dir=None):
        build_dir = build_dir or self.build_dir
        for filename, dest1, dest2 in list:
            src = build_dir+'/'+filename
            if not os.path.exists(src):
                continue
            debug("install if updated: %s" % filename)
            for dest_dir in (dest1, dest2):
                dest = dest_dir+'/'+filename
                if not os.path.exists(os.path.dirname(dest)):
                    os.makedirs(os.path.dirname(dest))
                if re.search('\.pvr\.plist$', src):
                    continue
                if re.search('\.plist$', src):
                    if os.path.exists(dest) and call(['diff', '-I', '<string>$TexturePacker:SmartUpdate:.*$</string>', src, dest], stdout=None, stderr=STDOUT) == 0:
                        continue
                else:   # general files
                    if call(['cmp', '--quiet', src, dest]) == 0:
                        continue
                if os.path.exists(dest):
                    os.remove(dest)
                info("install: %s -> %s" % (src, dest))
                copy2(src, dest)
        return True

    def install_generated(self, build_dir=None):
        build_dir = build_dir or self.build_dir
        # fixed pathes
        list = [
            (self.MASTER_JSON_SCHEMA_FILE,        self.master_schema_dir, self.org_master_schema_dir),
            (self.MASTER_JSON_DATA_FILE,          self.master_data_dir,   self.org_master_data_dir),
            (self.MASTER_BUNDLED_JSON_DATA_FILE,  self.master_data_dir,   self.org_master_data_dir),
            (self.MASTER_MACRO_FILE,              self.master_header_dir, self.org_master_header_dir),
            (self.MASTER_FBS_FILE,                self.master_fbs_dir,    self.org_master_fbs_dir),
            (self.MASTER_BIN_FILE,                self.master_bin_dir,    self.org_master_bin_dir),
            (self.MASTER_BUNDLED_BIN_FILE,        self.master_bin_dir,    self.org_master_bin_dir),
            (self.MASTER_HEADER_FILE,             self.master_header_dir, self.org_master_header_dir),
            (self.MASTER_MD5_FILE,                self.master_header_dir, self.org_master_header_dir),
            (self.EDITOR_MASTER_JSON_SCHEMA_FILE, self.master_schema_dir, self.org_master_schema_dir),
            (self.EDITOR_MASTER_JSON_DATA_FILE,   self.master_data_dir,   self.org_master_data_dir),
            (self.EDITOR_MASTER_MACRO_FILE,       self.master_header_dir, self.org_master_header_dir),
            (self.EDITOR_MASTER_FBS_FILE,         self.master_fbs_dir,    self.org_master_fbs_dir),
            (self.EDITOR_MASTER_BIN_FILE,         self.master_bin_dir,    self.org_master_bin_dir),
            (self.EDITOR_MASTER_HEADER_FILE,      self.master_header_dir, self.org_master_header_dir),
            (self.EDITOR_MASTER_MD5_FILE,         self.master_header_dir, self.org_master_header_dir),
            (self.USER_CLASS_FILE,                self.user_class_dir,    self.org_user_class_dir),
            (self.USER_JSON_SCHEMA_FILE,          self.user_schema_dir,   self.org_user_schema_dir),
            (self.USER_HEADER_FILE,               self.user_header_dir,   self.org_user_header_dir),
            (self.USER_MD5_FILE,                  self.user_header_dir,   self.org_user_header_dir),
        ]
        # spine
        for spine_path in glob("%s/*Spine/*" % build_dir):
            spine_path = re.sub('^'+build_dir+'/', '', spine_path)
            list.append((spine_path, self.spine_dir, self.org_spine_dir))
        # font
        for font_path in glob("%s/*.fnt" % build_dir):
            font_path = re.sub('^'+build_dir+'/', '', font_path)
            png_path  = re.sub('.fnt$', '.png', font_path)
            list.append((font_path, self.font_dir, self.font_dir)) # self.org_font_dir
            list.append((png_path,  self.font_dir, self.font_dir)) # self.org_font_dir
        # weapon
        for weapon_path in glob("%s/weapon/*.atlas" % build_dir):
            weapon_path = re.sub('^'+build_dir+'/', '', weapon_path)
            png_path  = re.sub('.atlas$', '.png', weapon_path)
            list.append((weapon_path, self.files_dir, self.org_files_dir))
            list.append((png_path,  self.files_dir, self.org_files_dir))
        # webviews
        for root, envs, files in os.walk(os.path.join(build_dir, 'webview')):
            for env in envs:
                if root != os.path.join(build_dir, 'webview'):
                    continue
                for sub_root, platforms, sub_files in os.walk(os.path.join(root, env)):
                    for platform in platforms:
                        webviews_json_path = os.path.join('webview', env, platform, 'webviews.json')
                        list.append((
                            webviews_json_path,
                            os.path.join(self.main_dir),
                            os.path.join(self.org_main_dir)
                        ))

        return self.install_list(list, build_dir)

    def install_texture(self, build_dir=None, files_dir=None, org_files_dir=None, texturepacker_dir=None, org_texturepacker_dir=None, imesta_dir=None, org_imesta_dir=None):
        build_dir             = build_dir             or self.build_dir
        files_dir             = files_dir             or self.files_dir
        texturepacker_dir     = texturepacker_dir     or self.texturepacker_dir
        imesta_dir            = imesta_dir            or self.imesta_dir
        org_files_dir         = org_files_dir         or self.org_files_dir
        org_texturepacker_dir = org_texturepacker_dir or self.org_texturepacker_dir
        org_imesta_dir        = org_imesta_dir        or self.org_imesta_dir

        # install texture packer output
        list = []
        for texture_build_dir in ("areaAtlas", "ui"):
            for root, dirs, files in os.walk("%s/%s" % (build_dir, texture_build_dir)):
                for file in files:
                    path = build_file = os.path.join(root, file)
                    path = re.sub('^'+build_dir+'/', '', path)
                    for tp_dir, im_dir in ((texturepacker_dir, imesta_dir), (org_texturepacker_dir, org_imesta_dir)):
                        # when texture packer outputs are updated, must rebuild it by imesta
                        packer_file = os.path.join(tp_dir, path)
                        imesta_file = os.path.join(im_dir, path)
                        if os.path.exists(packer_file) and os.path.exists(imesta_file) and call(['cmp', '--quiet', build_file, packer_file]) != 0:
                            base, ext = os.path.splitext(imesta_file)
                            for im_file in glob(base+'.*'):
                                os.remove(im_file)
                    list.append((path, texturepacker_dir, org_texturepacker_dir))
        self.install_list(list, build_dir)

        # select imesta or texture packer output and install
        for dest_dir, tp_dir, im_dir in ((files_dir, texturepacker_dir, imesta_dir), (org_files_dir, org_texturepacker_dir, org_imesta_dir)):
            for root, dirs, files in os.walk(tp_dir):
                update_files = []
                for file in files:
                    path = packer_file = os.path.join(root, file)
                    path = re.sub('^'+tp_dir+'/', '', path)
                    base, ext = os.path.splitext(path)
                    update_files.append((packer_file, os.path.join(dest_dir, path)))
                    for imesta_file in glob(os.path.join(im_dir, base+'.*')):
                        update_files.append((imesta_file, os.path.join(dest_dir, re.sub('^'+im_dir+'/', '', imesta_file))))
                for src, dest in update_files:
                    debug("install texture if updated: %s" % src)
                    if call(['cmp', '--quiet', src, dest]) == 0:
                        continue
                    info("install texture: %s -> %s" % (src, dest))
                    if not os.path.exists(os.path.dirname(dest)):
                        os.makedirs(os.path.dirname(dest))
                    copy2(src, dest)

    def install_manifest(self, build_dir=None):
        build_dir = build_dir or self.build_dir
        # TODO obsoleted all-in-one manifest
        list = [
            (self.PROJECT_MANIFEST_FILE, self.manifest_dir, self.org_manifest_dir),
            (self.VERSION_MANIFEST_FILE, self.manifest_dir, self.org_manifest_dir),
            (self.ASSET_LIST_FILE,       self.manifest_dir, self.org_manifest_dir),
            (self.LOCATION_FILE_LIST,    self.manifest_dir, self.org_manifest_dir),
            (self.CHARACTER_FILE_LIST,   self.manifest_dir, self.org_manifest_dir),
            (self.UI_FILE_LIST,          self.manifest_dir, self.org_manifest_dir),
        ]
        phased_manifests  = glob(build_dir+'/'+self.PROJECT_MANIFEST_FILE+'.*')
        phased_manifests += glob(build_dir+'/'+self.VERSION_MANIFEST_FILE+'.*')
        for manifest_path in phased_manifests:
            manifest_path = re.sub('^'+build_dir+'/', '', manifest_path)
            list.append((manifest_path, self.manifest_dir, self.org_manifest_dir))
        for manifest_path in glob(build_dir+'/'+self.PHASE_MANIFEST_FILE+'.*'):
            manifest_path = re.sub('^'+build_dir+'/', '', manifest_path)
            list.append((manifest_path, self.manifest_phase_dir, self.org_manifest_phase_dir))
        return self.install_list(list, build_dir)

    def build_webviews(self, root_dir=None, build_dir=None, env=None):
        root_dir  = root_dir  or self.main_dir
        build_dir = build_dir or self.build_dir
        env       = env       or 'dev'
        if not os.path.exists(root_dir+'/webview'):
            return True

        cmdline = [self.update_webviews_bin, 'update', '--root-dir', root_dir, '--build-dir', build_dir, '--environment', env, '--skip-sync-root', '1']
        info(' '.join(cmdline))
        check_call(cmdline)
        return True

    def deploy_webviews(self, root_dir=None, build_dir=None, env=None):
        root_dir  = root_dir  or self.main_dir
        build_dir = build_dir or self.build_dir
        env       = env       or 'dev'
        if not os.path.exists(root_dir+'/webview'):
            return True
        
        cmdline = [self.update_webviews_bin, 'deploy', '--root-dir', root_dir, '--build-dir', self.build_dir, '--environment', env]
        info(' '.join(cmdline))
        check_call(cmdline)
        return True

    def build_asset_list(self, src_list_file=None, dest_list_file=None):
        src_list_file  = src_list_file  or self.master_manifest_dir+'/'+self.ASSET_LIST_FILE
        dest_list_file = dest_list_file or self.build_dir+'/'+self.ASSET_LIST_FILE

        asset_list = OrderedDict()
        with open(src_list_file, 'r') as f:
            asset_list = json.load(f, object_pairs_hook=OrderedDict)
            if not self.target in asset_list:
                asset_list.append(self.target)

        info("available asset versions = "+", ".join(asset_list))
        with open(dest_list_file, 'w') as f:
            json.dump(asset_list, f, indent=2)
        os.chmod(dest_list_file, 0664)
        return True

    # create manifest json from
    def build_manifest(self, asset_version=None, dest_project_manifest=None, dest_version_manifest=None, url_project_manifest=None, url_version_manifest=None, filter_file=None, location_list=None, character_list=None, ui_list=None):
        asset_version           = asset_version or self.asset_version
        dest_project_manifest   = dest_project_manifest or self.build_dir+'/'+self.PROJECT_MANIFEST_FILE
        dest_version_manifest   = dest_version_manifest or self.build_dir+'/'+self.VERSION_MANIFEST_FILE
        url_project_manifest    = url_project_manifest or self.DEV_CDN_URL+'/'+self.asset_version_dir+'/'+self.PROJECT_MANIFEST_FILE
        url_version_manifest    = url_version_manifest or self.DEV_CDN_URL+'/'+self.asset_version_dir+'/'+self.VERSION_MANIFEST_FILE
        url_asset               = self.DEV_CDN_URL+'/'
        location_list           = self.build_dir+'/'+self.LOCATION_FILE_LIST
        character_list          = self.build_dir+'/'+self.CHARACTER_FILE_LIST
        ui_list                 = self.build_dir+'/'+self.UI_FILE_LIST
        base_filter_file        = self.master_distribution_dir+'/dev_ios.list'
        if not filter_file:
            real_filter_file = base_filter_file
        else:
            real_filter_file = self.build_dir+'/'+os.path.basename(filter_file)+'.tmp'
            with open(real_filter_file, 'w') as dest:
                for cat_file in (base_filter_file, filter_file):
                    with open(cat_file, 'r') as src:
                        content = src.read()
                        dest.write(content+'\n')

        if self.is_master:
            reference_manifest = self.master_manifest_dir+'/'+self.REFERENCE_MANIFEST_FILE
            keep_ref_entries   = []
            validate_filter    = ['--validate-filter']
        else:
            reference_manifest = self.master_manifest_dir+'/'+self.PROJECT_MANIFEST_FILE
            keep_ref_entries   = ['--keep-ref-entries']
            validate_filter    = []

        info("build manifest: %s + %s" % (os.path.basename(dest_project_manifest), os.path.basename(dest_version_manifest)))
        info("reference manifest: %s" % reference_manifest)
        info("filter file: %s" % filter_file)

        cmdline = [self.manifest_generate_bin, dest_project_manifest, dest_version_manifest,
                   asset_version, url_project_manifest, url_version_manifest, url_asset,
                   self.remote_dir_asset, self.main_dir+'/contents', 
                   "--ref", reference_manifest, '--filter', real_filter_file, 
                   '--location-list', location_list, '--character-list', character_list, '--ui-list', ui_list] \
                           + keep_ref_entries + validate_filter

        info(' '.join(cmdline))
        check_call(cmdline)
        return True

    def build_manifest_queue(self, src_dir=None, project_dir=None, phase_dir=None):
        src_dir     = src_dir     or self.master_distribution_dir
        project_dir = project_dir or self.build_dir
        phase_dir   = phase_dir   or self.build_dir
        manifest_paths = []

        # create phased manifests
        phase_list = glob(src_dir+'/phase_*.list')
        for filter_file in phase_list:
            m = re.match('phase_([0-9]+).list', os.path.basename(filter_file))
            phase = m.group(1)
            dest_project_manifest = os.path.join(project_dir, self.PROJECT_MANIFEST_FILE+'.'+phase)
            dest_version_manifest = os.path.join(project_dir, self.VERSION_MANIFEST_FILE+'.'+phase)
            url_project_manifest  = self.DEV_CDN_URL+'/'+self.asset_version_dir+'/'+self.PROJECT_MANIFEST_FILE+'.'+phase
            url_version_manifest  = self.DEV_CDN_URL+'/'+self.asset_version_dir+'/'+self.VERSION_MANIFEST_FILE+'.'+phase
            self.build_manifest(dest_project_manifest = dest_project_manifest, dest_version_manifest = dest_version_manifest, url_project_manifest = url_project_manifest, url_version_manifest = url_version_manifest, filter_file = filter_file)
            manifest_paths.append(dest_project_manifest)

        # last one (all-in-one)
        phase = str(len(phase_list)+1)
        dest_project_manifest = os.path.join(project_dir, self.PROJECT_MANIFEST_FILE+'.'+phase)
        dest_version_manifest = os.path.join(project_dir, self.VERSION_MANIFEST_FILE+'.'+phase)
        url_project_manifest  = self.DEV_CDN_URL+'/'+self.asset_version_dir+'/'+self.PROJECT_MANIFEST_FILE+'.'+phase
        url_version_manifest  = self.DEV_CDN_URL+'/'+self.asset_version_dir+'/'+self.VERSION_MANIFEST_FILE+'.'+phase
        self.build_manifest(dest_project_manifest = dest_project_manifest, dest_version_manifest = dest_version_manifest, url_project_manifest = url_project_manifest, url_version_manifest = url_version_manifest)
        manifest_paths.append(dest_project_manifest)

        # build manifest queue
        cmdline = [self.manifest_queue_bin, '--project-dir', project_dir, '--phase-dir', phase_dir, '--remote-dir', self.remote_dir_asset+'/manifests', '--asset-dir', self.main_dir+'/contents'] + manifest_paths
        info(' '.join(cmdline))
        check_call(cmdline)
        return True

    def deploy_git_repo(self):
        if not self.is_master or not self.git_dir:
            return

        info("deploy to git repo: %s -> %s" % (self.main_dir, self.git_dir))
        cmdline = ['rsync', '-ac', '--exclude', '.DS_Store', '--exclude', '.git', '--delete', self.main_dir+'/', self.git_dir]
        info(' '.join(cmdline))
        check_call(cmdline)
        return True

    def deploy_dev_cdn(self):
        #FIXME dev.project.manifest and dev.version.manifest are deprecated 
        copy2(self.build_dir+'/'+self.PROJECT_MANIFEST_FILE, self.build_dir+'/dev.project.manifest')
        copy2(self.build_dir+'/'+self.VERSION_MANIFEST_FILE, self.build_dir+'/dev.version.manifest')

        manifests  = glob(self.build_dir+'/'+self.PROJECT_MANIFEST_FILE+'*')
        manifests += glob(self.build_dir+'/'+self.VERSION_MANIFEST_FILE+'*')
        manifests += [self.build_dir+'/dev.project.manifest', self.build_dir+'/dev.version.manifest']
        for manifest_path in manifests:
            with open(manifest_path, 'r+') as f:
                manifest = json.load(f, object_pairs_hook=OrderedDict)
                manifest["version"] += " "+self.timestamp
                f.seek(0)
                f.truncate(0)
                json.dump(manifest, f, indent=2)

        rsync = ['rsync', '-ac']
        #rsync = ['rsync', '-crltvO']
        #rsync = ['rsync', '-crltvO', '-e', "ssh -i "+DEV_SSH_KEY]
        rsync.extend(['--exclude', '.DS_Store'])

        dest_dir = self.cdn_dir+'/'+self.asset_version_dir
        if not os.path.exists(dest_dir):
            os.makedirs(dest_dir)
        info("deploy to dev cdn: %s -> %s: " % (self.main_dir, dest_dir))

        check_call("find " + self.main_dir+'/contents' + " -type f -print | xargs chmod 664", shell=True)
        check_call("find " + self.main_dir+'/contents' + " -type d -print | xargs chmod 775", shell=True)
        info("deploy to dev cdn: %s" % self.main_dir+'/contents/')
        check_call(rsync + ['--delete', self.main_dir+'/contents/', dest_dir+'/contents'])
        check_call(['chmod', '775', dest_dir+'/contents'])
        info("deploy to dev cdn: manifests: %s" % ', '.join(manifests))
        check_call(rsync + manifests + [dest_dir+'/'])
        info("deploy to dev cdn: %s" % self.ASSET_LIST_FILE)
        check_call(rsync + [self.build_dir+'/'+self.ASSET_LIST_FILE, self.cdn_dir+'/'])
        info("deploy to dev cdn: done")
        return True

    def deploy_s3_cdn(self):
        if not os.path.exists(os.path.normpath(os.path.expanduser(self.S3_CREDENTIALS_FILE))):
            warning("aws credentials file is not found. skip deploy to s3")
            return False

        manifests  = glob(self.build_dir+'/'+self.PROJECT_MANIFEST_FILE+'*')
        manifests += glob(self.build_dir+'/'+self.VERSION_MANIFEST_FILE+'*')
        manifests += [self.build_dir+'/dev.project.manifest', self.build_dir+'/dev.version.manifest']
        phase_manifests = glob(self.build_dir+'/'+self.PHASE_MANIFEST_FILE+'.*')
        for manifest_path in manifests + phase_manifests:
            with open(manifest_path, 'r+') as f:
                manifest = json.load(f, object_pairs_hook=OrderedDict)
                prevUrl = manifest["packageUrl"]
                #manifest["version"] += " "+self.timestamp
                manifest["packageUrl"] = self.S3_CDN_URL+'/'
                manifest["remoteManifestUrl"] = re.sub('^'+prevUrl, self.S3_CDN_URL+'/', manifest["remoteManifestUrl"])
                manifest["remoteVersionUrl"]  = re.sub('^'+prevUrl, self.S3_CDN_URL+'/', manifest["remoteVersionUrl"])
                f.seek(0)
                f.truncate(0)
                json.dump(manifest, f, indent=2)

        info("deploy to s3 cdn: %s -> %s: %s" % (self.main_dir, self.S3_INTERNAL_URL, self.S3_CDN_URL))

        aws_s3 = ['aws', 's3']
        s3_internal_url = self.S3_INTERNAL_URL+'/'+self.asset_version_dir
        info("deploy to s3: %s" % self.main_dir+'/contents/')
        check_call(aws_s3 + ['sync', '--exclude', '.DS_Store', self.main_dir+'/contents/', s3_internal_url+'/contents'])
        for manifest in manifests:
            info("deploy to s3: %s" % os.path.basename(manifest))
            check_call(aws_s3 + ['cp', manifest, s3_internal_url+'/'])
        for manifest in phase_manifests:
            info("deploy to s3: %s" % os.path.basename(manifest))
            check_call(aws_s3 + ['cp', manifest, s3_internal_url+'/contents/manifests/'])
        info("deploy to s3: %s" % self.ASSET_LIST_FILE)
        check_call(aws_s3 + ['cp', self.build_dir+'/'+self.ASSET_LIST_FILE, self.S3_INTERNAL_URL+'/'])
        info("deploy to s3 cdn: done")
        return True

    # do all processes
    def build(self):
        self.setup_dir()

        # for standard master data
        self.build_master_json()
        self.merge_editor_schema()
        self.merge_editor_data()
        self.sort_master_json()
        #self.build_master_macro()
        self.build_master_fbs()
        self.build_master_bin()
        self.build_master_bundled_bin()

        # for editor master data
        editor_schema_file = self.build_dir+'/'+self.EDITOR_MASTER_JSON_SCHEMA_FILE
        editor_data_file   = self.build_dir+'/'+self.EDITOR_MASTER_JSON_DATA_FILE
        editor_macro_file  = self.build_dir+'/'+self.EDITOR_MASTER_MACRO_FILE
        editor_fbs_file    = self.build_dir+'/'+self.EDITOR_MASTER_FBS_FILE
        editor_bin_file    = self.build_dir+'/'+self.EDITOR_MASTER_BIN_FILE
        editor_header_file = self.build_dir+'/'+self.EDITOR_MASTER_HEADER_FILE
        editor_md5_file    = self.build_dir+'/'+self.EDITOR_MASTER_MD5_FILE
        editor_md5_define  = self.EDITOR_MASTER_MD5_DEFINE
        self.build_master_json(dest_schema=editor_schema_file, dest_data=editor_data_file, except_json=True)
        self.sort_master_json(src_schema=editor_schema_file, src_data=editor_data_file)
        self.build_master_macro(src_json=editor_data_file, dest_macro=editor_macro_file)
        self.build_master_fbs(src_json=editor_schema_file, dest_fbs=editor_fbs_file)
        self.build_master_bin(src_json=editor_data_file, src_fbs=editor_fbs_file, dest_bin=editor_bin_file, dest_header=editor_header_file, dest_md5=editor_md5_file, dest_define=editor_md5_define)

        # user data
        self.build_user_class()

        # verify
        self.verify_master_json()

        # asset
        self.build_spine()
        self.build_weapon()
        self.build_area_atlas()
        self.build_ui_atlas()
        self.build_font()

        # webviews
        self.build_webviews()

        # install
        self.install_generated()
        self.install_texture()
        self.build_asset_list()
        self.verify_master_json(src_user_schema = False, src_user_data = False, verify_file_reference = True)

        # setup to deploy
        self.build_manifest()
        self.build_manifest_queue()
        self.install_manifest()

        return True

    # deploy to cdn
    def deploy(self):
        self.deploy_git_repo()
        self.deploy_dev_cdn()
        self.deploy_s3_cdn()
        self.deploy_webviews()
        return True

    # clean up
    def cleanup(self):
        info("cleanup under: %s" % self.build_dir)
        for path in glob(self.build_dir+'/*'):
            if os.path.basename(path) in ('areaAtlas', 'ui'):
                info("exclude to clean up: "+path)
                continue
            elif os.path.isfile(path):
                os.remove(path)
            elif os.path.isdir(path):
                rmtree(path)
        return True

if __name__ == '__main__':
    sys.stdout = codecs.lookup('utf_8')[-1](sys.stdout)
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawTextHelpFormatter,
        description = 'build asset and master data', 
        epilog = """\
commands:
  build    do build, deploy and cleanup
  debug    just do build, do not deploy and cleanup
  clean    cleanup build dir

examples:
  build all for 'kms_master_data'
    $ cd kms_master_data/hook
    $ ./script/build.py build master

  build on local (for development)
    $ ./script/build.py debug master --log-level DEBUG

  clean up after build on local (for development)
    $ ./script/build.py clean master

  build all for 'kms_xxx.yyy_asset'
    $ kms_master_asset/hook/build.py build xxx.yyy
        """)
    parser.add_argument('command',         help = 'build command (build|debug)')
    parser.add_argument('target',          help = 'target name (e.g. master, kiyoto.suzuki, ...) default: master')
    parser.add_argument('--asset-version', help = 'asset version. default: <target>.<unix-timestamp>')
    parser.add_argument('--master-dir',    help = 'master asset directory. default: same as script top')
    parser.add_argument('--main-dir',      help = 'asset generated directory. default: same as script top')
    parser.add_argument('--build-dir',     help = 'build directory. default: ~/kms_asset_builder_build')
    parser.add_argument('--mirror-dir',    help = 'mirror directory. default: ~/kms_asset_builder_mirror')
    parser.add_argument('--cdn-dir',       help = 'cdn directory to deploy. default: /var/www/cdn')
    parser.add_argument('--git-dir',       help = 'git directory to deploy. default: (not to deploy)')
    parser.add_argument('--log-level',     help = 'log level (WARNING|INFO|DEBUG). default: INFO')
    args = parser.parse_args()
    logging.basicConfig(level = args.log_level or "INFO", format = '%(asctime)-15s %(levelname)s %(message)s')

    asset_builder = AssetBuilder(command = args.command, target = args.target, asset_version = args.asset_version, main_dir = args.main_dir, master_dir = args.master_dir, build_dir = args.build_dir, mirror_dir = args.mirror_dir, cdn_dir = args.cdn_dir, git_dir = args.git_dir)
    try:
        if args.command in ('build', 'debug'):
            asset_builder.build()
        if args.command in ('build'):
            asset_builder.deploy()
    finally:
        if args.command in ('clean', 'build'):
            asset_builder.cleanup()
    exit(0)

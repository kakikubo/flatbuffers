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
import logging
from time import strftime
from subprocess import check_call, check_output, call
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

        self.manifest_dir             = self.main_dir+'/manifests'
        self.master_schema_dir        = self.main_dir+'/master_derivatives'
        self.master_data_dir          = self.main_dir+'/master_derivatives'
        self.master_fbs_dir           = self.main_dir+'/master_derivatives'
        self.master_bin_dir           = self.main_dir+'/contents/master'
        self.master_header_dir        = self.main_dir+'/master_header'
        self.user_class_dir           = self.main_dir+'/user_header'
        self.user_schema_dir          = self.main_dir+'/user_derivatives'
        self.user_header_dir          = self.main_dir+'/user_header'
        self.files_dir                = self.main_dir+'/contents/files'
        self.user_data_dir            = self.main_dir+'/contents/files/user_data'
        self.spine_dir                = self.main_dir+'/contents/files/spine'
        self.font_dir                 = self.main_dir+'/contents/files/font'
        self.weapon_dir               = self.main_dir+'/contents/files/weapon'
        self.ui_dir                   = self.main_dir+'/contents/files/ui'
        self.area_texture_dir         = self.main_dir+'/contents/files/area'
        self.distribution_dir         = self.main_dir+'/distribution'

        self.org_manifest_dir         = self.org_main_dir+'/manifests'
        self.org_master_schema_dir    = self.org_main_dir+'/master_derivatives'
        self.org_master_data_dir      = self.org_main_dir+'/master_derivatives'
        self.org_master_fbs_dir       = self.org_main_dir+'/master_derivatives'
        self.org_master_bin_dir       = self.org_main_dir+'/contents/master'
        self.org_master_header_dir    = self.org_main_dir+'/master_header'
        self.org_user_class_dir       = self.org_main_dir+'/user_header'
        self.org_user_schema_dir      = self.org_main_dir+'/user_derivatives'
        self.org_user_header_dir      = self.org_main_dir+'/user_header'
        self.org_files_dir            = self.org_main_dir+'/contents/files'
        self.org_user_data_dir        = self.org_main_dir+'/contents/files/user_data'
        self.org_spine_dir            = self.org_main_dir+'/contents/files/spine'
        self.org_font_dir             = self.org_main_dir+'/contents/files/font'
        self.org_weapon_dir           = self.org_main_dir+'/contents/files/weapon'
        self.org_ui_dir               = self.org_main_dir+'/contents/files/ui'
        self.org_area_texture_dir     = self.org_main_dir+'/contents/files/area'
        self.org_distribution_dir     = self.org_main_dir+'/distribution'

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
        self.master_user_data_dir     = self.master_dir+'/contents/files/user_data'

        main_editor_schema = self.main_editor_schema_dir+'/editor_schema.json'
        self.editor_schema = main_editor_schema if os.path.exists(main_editor_schema) else self.master_editor_schema_dir+'/editor_schema.json'

        self.manifest_bin           = self_dir+'/manifest_generate.py'
        self.xls2json_bin           = self_dir+'/master_data_xls2json.py'
        self.json2fbs_bin           = self_dir+'/json2fbs.py'
        self.json2macro_bin         = self_dir+'/json2macro.py'
        self.flatc_bin              = self_dir+'/flatc'
        self.fbs2class_bin          = self_dir+'/fbs2class.py'
        self.json2font_bin          = self_dir+'/json2font.py'
        self.sort_master_json_bin   = self_dir+'/sort-master-json.py'
        self.verify_master_json_bin = self_dir+'/verify_master_json.py'
        self.strip_master_json_bin  = self_dir+'/strip_master_json.py'
        self.delete_element_bin     = self_dir+'/delete-element.py'
        self.make_atlas_bin         = self_dir+'/make_atlas.py'
        self.pack_texture_bin       = self_dir+'/pack_texture.py'
        self.pack_area_texture_bin  = self_dir+'/make_area_atlas.py'
        
        self.PROJECT_MANIFEST_FILE          = 'dev.project.manifest'
        self.VERSION_MANIFEST_FILE          = 'dev.version.manifest'
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
        self.MASTER_MD5_FILE                = 'master_data.generated.h.md5'
        self.EDITOR_MASTER_JSON_SCHEMA_FILE = 'editor_master_schema.json'
        self.EDITOR_MASTER_JSON_DATA_FILE   = 'editor_master_data.json'
        self.EDITOR_MASTER_MACRO_FILE       = 'EditorMasterAccessors.h'
        self.EDITOR_MASTER_FBS_FILE         = 'editor_master_data.fbs'
        self.EDITOR_MASTER_BIN_FILE         = 'editor_master_data.bin'
        self.EDITOR_MASTER_HEADER_FILE      = 'editor_master_data_generated.h'
        self.EDITOR_MASTER_MD5_FILE         = 'editor_master_data_generated.h.md5'
        self.MASTER_FBS_ROOT_NAME           = 'MasterDataFBS'
        self.MASTER_FBS_NAMESPACE           = 'kms.masterdata'
        self.USER_FBS_FILE                  = 'user_data.fbs'
        self.USER_CLASS_FILE                = 'user_data.h'
        self.USER_MD5_FILE                  = 'user_data.h.md5'
        self.USER_JSON_SCHEMA_FILE          = 'user_schema.json'
        self.USER_HEADER_FILE               = 'user_data_generated.h'
        self.USER_FBS_ROOT_NAME             = 'UserDataFBS'
        self.USER_FBS_NAMESPACE             = 'kms.userdata'
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

    # get editor data files
    def _get_editor_files(self):
        editor_dirs = (self.master_editor_dir, self.main_editor_dir)
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
        return editor_files.values()

    def _write_md5(self, src, dest):
        cmdline = ['md5', src]
        out = check_output(cmdline)
        m = re.match('.*=\s*([^\s]+)', out)
        if m:
            with open(dest, 'w') as f:
                f.write(m.group(1))
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
        debug(' '.join(cmdline))
        check_call(cmdline)
        return True

    # merge editor's json data into the master json data
    def merge_editor_file(self):
        for master_file, editor_files in \
                ((self.build_dir+'/'+self.MASTER_JSON_DATA_FILE, self._get_editor_files()), \
                (self.build_dir+'/'+self.MASTER_JSON_SCHEMA_FILE, [self.editor_schema])):
            with open(master_file, 'r') as f:
                json_data = json.loads(f.read(), object_pairs_hook=OrderedDict)

            for editor_file in editor_files:
                info("merge editor master file: %s + %s" % (os.path.basename(master_file), os.path.basename(editor_file)))
                with open(editor_file, 'r') as f:
                    editor_json_data = json.loads(f.read(), object_pairs_hook=OrderedDict)
                for key in editor_json_data:
                    data = editor_json_data[key]
                    if '_' in key:
                        a = key.split('_')
                        key = a[0]
                        if a[1] == "item":
                            if not key in json_data:
                                editor_json_data[key] = []
                            json_data[key].append(data)
                    else:
                        json_data[key] = data

            with open(master_file, 'w') as f:
                j = json.dumps(json_data, ensure_ascii = False, indent = 4)
                f.write(j.encode("utf-8"))

    # sort master json
    def sort_master_json(self, src_schema=None, src_data=None):
        src_schema = src_schema or self.build_dir+'/'+self.MASTER_JSON_SCHEMA_FILE
        src_data   = src_data or self.build_dir+'/'+self.MASTER_JSON_DATA_FILE
        info("sort master json: %s + %s" % (os.path.basename(src_schema), os.path.basename(src_data)))

        cmdline = [self.sort_master_json_bin, src_schema, src_data, src_data]
        debug(' '.join(cmdline))
        check_call(cmdline)
        return True

    def verify_master_json(self, src_schema=None, src_data=None, asset_dirs=None, src_user_schema=None, src_user_dirs=None):
        src_schema      = src_schema or self.build_dir+'/'+self.MASTER_JSON_SCHEMA_FILE
        src_data        = src_data or self.build_dir+'/'+self.MASTER_JSON_DATA_FILE
        asset_dirs      = asset_dirs or [self.org_main_dir, self.org_master_dir]
        src_user_dirs   = src_user_dirs or [self.user_data_dir, self.master_user_data_dir]
        if not src_user_schema:
            for user_schema in (self.build_dir+'/'+self.USER_JSON_SCHEMA_FILE, self.master_user_schema_dir+'/'+self.USER_JSON_SCHEMA_FILE):
                if os.path.exists(user_schema):
                    src_user_schema = user_schema
                    break
        info("verify master data: %s + %s" % (os.path.basename(src_schema), os.path.basename(src_data)))

        cmdline = [self.verify_master_json_bin, src_schema, src_data, '--asset-dir'] + asset_dirs + ['--user-schema', src_user_schema, '--user-dir'] + src_user_dirs
        debug(' '.join(cmdline))
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
        debug(' '.join(cmdline))
        check_call(cmdline)
        return True

    # create macro from json
    def build_master_macro(self, src_json=None, dest_macro=None):
        src_json   = src_json   or self.build_dir+'/'+self.MASTER_JSON_SCHEMA_FILE
        dest_macro = dest_macro or self.build_dir+'/'+self.MASTER_MACRO_FILE
        info("build master macro: %s" % os.path.basename(dest_macro))

        cmdline = [self.json2macro_bin, src_json, dest_macro]
        debug(' '.join(cmdline))
        check_call(cmdline)
        return True

    # create bin+header from json+fbs
    def build_master_bin(self, src_json=None, src_fbs=None, dest_bin=None, dest_header=None, dest_md5=None):
        src_json    = src_json    or self.build_dir+'/'+self.MASTER_JSON_DATA_FILE
        src_fbs     = src_fbs     or self.build_dir+'/'+self.MASTER_FBS_FILE
        dest_bin    = dest_bin    or self.build_dir+'/'+self.MASTER_BIN_FILE
        dest_header = dest_header or self.build_dir+'/'+self.MASTER_HEADER_FILE
        dest_md5    = dest_md5    or self.build_dir+'/'+self.MASTER_MD5_FILE
        dest_dir    = os.path.dirname(dest_bin)
        info("build master bin: %s + %s" % (os.path.basename(dest_bin), os.path.basename(dest_header)))
        if os.path.dirname(dest_bin) != os.path.dirname(dest_header):
            raise Exception("%s and %s must be same dir" % (dest_bin, dest_header))

        cmdline = [self.flatc_bin, '-c', '-b', '-o', dest_dir, src_fbs, src_json]
        debug(' '.join(cmdline))
        check_call(cmdline)

        return self._write_md5(dest_header, dest_md5)

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
        debug(' '.join(cmdline))
        check_call(cmdline)

        cmdline = [self.flatc_bin, '-b', '-o', dest_dir, src_fbs, dest_bundled_json]
        debug(' '.join(cmdline))
        check_call(cmdline)

        return True

    # strip spine character animations
    def build_spine(self, src_xlsxes=None, src_spine_dir=None, dest_dir=None):
        src_xlsxes    = src_xlsxes    or self._get_xlsxes()
        src_spine_dir = src_spine_dir or self.spine_dir
        dest_dir      = dest_dir      or self.build_dir

        config = [
            ['characterSpine', '350:600'],
            ['npcSpine',       '450:550'],
            ['snpcSpine',      '350:550']
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
                debug(' '.join(cmdline))
                check_call(cmdline)
        return True

    # create weapon atlas from json
    def build_weapon(self, src_xlsxes=None, src_weapon_dir=None, dest_dir=None):
        src_xlsxes     = src_xlsxes     or self._get_xlsxes()
        src_weapon_dir = src_weapon_dir or self.weapon_dir
        dest_dir       = dest_dir       or self.build_dir

        if not os.path.exists(src_weapon_dir):
            return True

        for xlsx in self._get_xlsxes():
            sheets = self._get_xlsx_sheets(xlsx)
            for sheet in sheets:
                if sheet == "weapon":
                    dest_weapon_dir = dest_dir+'/'+"weapon"
                    if not os.path.exists(dest_weapon_dir):
                        os.makedirs(dest_weapon_dir)

                    info("build weapon atlas: %s:" % os.path.basename(xlsx))
                    cmdline = [self.make_atlas_bin, xlsx, "weapon", str(self.MASTER_DATA_ROW_START), "positionX", dest_weapon_dir]
                    debug(' '.join(cmdline))
                    check_call(cmdline)
        return True

    # create ui texture atlas by texture packer
    def build_ui(self, src_dir=None, dest_dir=None):
        src_dir  = src_dir  or self.ui_dir
        dest_dir = dest_dir or self.build_dir+'/ui'

        if not os.path.exists(src_dir):
            return True

        info("build ui texture atlas: %s:" % src_dir)
        cmdline = [self.pack_texture_bin, src_dir, dest_dir]
        debug(' '.join(cmdline))
        check_call(cmdline)
        return True

    # create ui texture atlas by texture packer
    def build_area_texture(self, src_dir=None, dest_dir=None):
        src_dir  = src_dir  or self.area_texture_dir
        dest_dir = dest_dir or self.build_dir+'/areaAtlas'

        if not os.path.exists(src_dir):
            return True

        info("build area texture atlas: %s:" % src_dir)
        cmdline = [self.pack_area_texture_bin, src_dir, dest_dir]
        debug(' '.join(cmdline))
        check_call(cmdline)
        return True

    # create class header from fbs
    def build_user_class(self, src_fbs=None, dest_class=None, dest_schema=None, dest_md5=None, namespace=None):
        src_fbs     = src_fbs     or self.main_schema_dir+'/'+self.USER_FBS_FILE
        dest_class  = dest_class  or self.build_dir+'/'+self.USER_CLASS_FILE
        dest_schema = dest_schema or self.build_dir+'/'+self.USER_JSON_SCHEMA_FILE
        dest_md5    = dest_md5    or self.build_dir+'/'+self.USER_MD5_FILE
        namespace   = namespace   or self.USER_FBS_NAMESPACE
        if not os.path.exists(src_fbs):
            return False

        info("build user class: %s + %s" % (os.path.basename(dest_class), os.path.basename(dest_schema)))
        cmdline = [self.fbs2class_bin, src_fbs, dest_class, dest_schema, '--namespace', namespace]
        debug(' '.join(cmdline))
        check_call(cmdline)

        return self._write_md5(dest_class, dest_md5)

    # create bin+header from json+fbs
    def build_user_header(self, src_json=None, src_fbs=None, dest_bin=None, dest_header=None):
        src_fbs     = src_fbs     or self.main_schema_dir+'/'+self.USER_FBS_FILE
        dest_header = dest_header or self.build_dir+'/'+self.USER_HEADER_FILE
        dest_dir    = os.path.dirname(dest_header)
        info("build user header: %s" % os.path.basename(dest_header))

        cmdline = [self.flatc_bin, '-c', '-o', dest_dir, src_fbs]
        debug(' '.join(cmdline))
        check_call(cmdline)
        return True

    # create fnt+png from json
    def build_font(self, src_json=None, src_gd_dir=None, dest_font_dir=None):
        # build font by GDCL
        src_json      = src_json      or self.build_dir+'/'+self.MASTER_JSON_DATA_FILE
        src_gd_dir    = src_gd_dir    or self.master_gd_dir
        dest_font_dir = dest_font_dir or self.build_dir
        cmdline = [self.json2font_bin, src_json, src_gd_dir, dest_font_dir]
        debug(' '.join(cmdline))
        check_call(cmdline)
        return True

    # copy all generated files 
    def install_list(self, list, build_dir=None):
        build_dir = build_dir or self.build_dir
        for filename, dest1, dest2 in list:
            src = build_dir+'/'+filename
            if not os.path.exists(src):
                continue
            info("install if updated: %s" % filename)
            for dest_dir in (dest1, dest2):
                dest = dest_dir+'/'+filename
                if not os.path.exists(os.path.dirname(dest)):
                    os.makedirs(os.path.dirname(dest))
                if re.search('\.plist$', src):
                    if os.path.exists(dest) and call(['diff', '-I', '<string>$TexturePacker:SmartUpdate:.*$</string>', src, dest]) == 0:
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
        for spine_path in glob("%s/*Spine/*.json" % build_dir):
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
        # packed area texture
        for root, dirs, files in os.walk("%s/areaAtlas" % build_dir):
            for file in files:
                path = os.path.join(root, file)
                path = re.sub('^'+build_dir+'/', '', path)
                list.append((path, self.files_dir, self.org_files_dir))
        # ui
        #for root, dirs, files in os.walk("%s/ui" % build_dir):
        #    for file in files:
        #        path = os.path.join(root, file)
        #        path = re.sub('^'+build_dir+'/', '', path)
        #        list.append((path, self.files_dir, self.org_files_dir))
        return self.install_list(list, build_dir)

    def install_manifest(self, build_dir=None):
        list = [
            (self.PROJECT_MANIFEST_FILE, self.manifest_dir, self.org_manifest_dir),
            (self.VERSION_MANIFEST_FILE, self.manifest_dir, self.org_manifest_dir),
            (self.ASSET_LIST_FILE,       self.manifest_dir, self.org_manifest_dir),
        ]
        return self.install_list(list, build_dir)

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

    def deploy_git_repo(self):
        if not self.is_master or not self.git_dir:
            return

        info("deploy to git repo: %s -> %s" % (self.main_dir, self.git_dir))
        cmdline = ['rsync', '-a', '--exclude', '.DS_Store', '--exclude', '.git', '--delete', self.main_dir+'/', self.git_dir]
        info(' '.join(cmdline))
        check_call(cmdline)
        return True

    # create manifest json from
    def build_manifest(self, asset_version=None, dest_project_manifest=None, dest_version_manifest=None):
        asset_version           = asset_version or self.asset_version
        dest_project_manifest   = dest_project_manifest or self.build_dir+'/'+self.PROJECT_MANIFEST_FILE
        dest_version_manifest   = dest_version_manifest or self.build_dir+'/'+self.VERSION_MANIFEST_FILE
        url_asset               = self.DEV_CDN_URL+'/'
        
        url_project_manifest  = self.DEV_CDN_URL+'/'+self.asset_version_dir+'/'+self.PROJECT_MANIFEST_FILE
        url_version_manifest  = self.DEV_CDN_URL+'/'+self.asset_version_dir+'/'+self.VERSION_MANIFEST_FILE
        if self.is_master:
            reference_manifest    = self.master_manifest_dir+'/'+self.REFERENCE_MANIFEST_FILE
            keep_ref_entries      = False
        else:
            reference_manifest    = self.master_manifest_dir+'/'+self.PROJECT_MANIFEST_FILE
            keep_ref_entries      = True

        info("build manifest: %s + %s" % (os.path.basename(dest_project_manifest), os.path.basename(dest_version_manifest)))
        info("reference manifest: %s" % reference_manifest)

        cmdline = [self.manifest_bin, dest_project_manifest, dest_version_manifest,
                   asset_version, url_project_manifest, url_version_manifest, url_asset,
                   self.remote_dir_asset, self.main_dir+'/contents', "--ref", reference_manifest]
        if keep_ref_entries:
          cmdline.append('--keep-ref-entries')
        debug(' '.join(cmdline))
        check_call(cmdline)
        return True

    def deploy_dev_cdn(self):
        project_file    = self.build_dir+'/'+self.PROJECT_MANIFEST_FILE
        version_file    = self.build_dir+'/'+self.VERSION_MANIFEST_FILE
        asset_list_file = self.build_dir+'/'+self.ASSET_LIST_FILE

        with open(project_file, 'r') as f:
            manifest = json.load(f, object_pairs_hook=OrderedDict)
        assets = manifest.get('assets')
        keep_files = []
        for key, asset in assets.iteritems():
            path = asset.get('path')
            if path == self.remote_dir_asset+"/"+key:
                keep_files.append(path)
        for root, dirs, files in os.walk(self.main_dir+'/contents'):
            for file in files:
                key = root.replace(self.main_dir+'/contents', self.remote_dir_asset)+'/'+file
                if not key in keep_files:
                    info("except from cdn: %s" % key)
                    os.remove(root+'/'+file)

        for manifest_file in (project_file, version_file):
            with open(manifest_file, 'r+') as f:
                manifest = json.load(f, object_pairs_hook=OrderedDict)
                manifest["version"] += " "+self.timestamp
                f.seek(0)
                f.truncate(0)
                json.dump(manifest, f, indent=2)

        rsync = ['rsync', '-a']
        #rsync = ['rsync', '-crltvO']
        #rsync = ['rsync', '-crltvO', '-e', "ssh -i "+DEV_SSH_KEY]
        rsync.extend(['--exclude', '.DS_Store'])

        dest_dir = self.cdn_dir+'/'+self.asset_version_dir
        if not os.path.exists(dest_dir):
            os.makedirs(dest_dir)
        info("deploy to dev cdn: %s -> %s: " % (self.main_dir, dest_dir))

        check_call("find " + self.main_dir+'/contents' + " -type f -print | xargs chmod 664", shell=True)
        check_call("find " + self.main_dir+'/contents' + " -type d -print | xargs chmod 775", shell=True)
        info("deploy %s" % self.main_dir+'/contents/')
        check_call(rsync + ['--delete', self.main_dir+'/contents/', dest_dir+'/contents'])
        check_call(['chmod', '775', dest_dir+'/contents'])
        info("deploy %s + %s" % (project_file, version_file))
        check_call(rsync + [project_file, version_file, dest_dir+'/'])
        info("deploy %s" % asset_list_file)
        check_call(rsync + [asset_list_file, self.cdn_dir+'/'])
        info("deploy to dev cdn: done")
        return True

    def deploy_s3_cdn(self):
        if not os.path.exists(os.path.normpath(os.path.expanduser(self.S3_CREDENTIALS_FILE))):
            warning("aws credentials file is not found. skip deploy to s3")
            return False

        project_file    = self.build_dir+'/'+self.PROJECT_MANIFEST_FILE
        version_file    = self.build_dir+'/'+self.VERSION_MANIFEST_FILE
        asset_list_file = self.build_dir+'/'+self.ASSET_LIST_FILE

        for manifest_file in (project_file, version_file):
            with open(manifest_file, 'r+') as f:
                manifest = json.load(f, object_pairs_hook=OrderedDict)
                prevUrl = manifest["packageUrl"]
                manifest["packageUrl"] = self.S3_CDN_URL+'/'
                manifest["remoteManifestUrl"] = re.sub('^'+prevUrl, self.S3_CDN_URL+'/', manifest["remoteManifestUrl"])
                manifest["remoteVersionUrl"]  = re.sub('^'+prevUrl, self.S3_CDN_URL+'/', manifest["remoteVersionUrl"])
                f.seek(0)
                f.truncate(0)
                json.dump(manifest, f, indent=2)

        info("deploy to s3 cdn: %s -> %s: %s" % (self.main_dir, self.S3_INTERNAL_URL, self.S3_CDN_URL))

        aws_s3 = ['aws', 's3']
        s3_internal_url = self.S3_INTERNAL_URL+'/'+self.asset_version_dir
        info("deploy %s" % self.main_dir+'/contents/')
        check_call(aws_s3 + ['sync', '--exclude', '.DS_Store', self.main_dir+'/contents/', s3_internal_url+'/contents'])
        info("deploy %s" % project_file)
        check_call(aws_s3 + ['cp', project_file, s3_internal_url+'/'])
        info("deploy %s" % version_file)
        check_call(aws_s3 + ['cp', version_file, s3_internal_url+'/'])
        info("deploy %s" % asset_list_file)
        check_call(aws_s3 + ['cp', asset_list_file, self.S3_INTERNAL_URL+'/'])
        info("deploy to s3 cdn: done")
        return True

    # do all processes
    def build(self):
        self.setup_dir()

        # for standard master data
        self.build_master_json()
        self.merge_editor_file()
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
        self.build_master_json(dest_schema=editor_schema_file, dest_data=editor_data_file, except_json=True)
        self.sort_master_json(src_schema=editor_schema_file, src_data=editor_data_file)
        self.build_master_macro(src_json=editor_data_file, dest_macro=editor_macro_file)
        self.build_master_fbs(src_json=editor_schema_file, dest_fbs=editor_fbs_file)
        self.build_master_bin(src_json=editor_data_file, src_fbs=editor_fbs_file, dest_bin=editor_bin_file, dest_header=editor_header_file, dest_md5=editor_md5_file)

        # user data
        self.build_user_class()

        # verify
        self.verify_master_json()

        # asset
        self.build_spine()
        self.build_weapon()
        #self.build_area_texture()
        #self.build_ui()
        self.build_font()

        # install
        self.install_generated()
        self.build_asset_list()
        self.deploy_git_repo() # FIXME can move to deploy?
        self.build_manifest()
        self.install_manifest()
        return True

    # deploy to cdn
    def deploy(self):
        self.deploy_dev_cdn()
        self.deploy_s3_cdn()
        return True

    # clean up
    def cleanup(self):
        info("cleanup: %s" % self.build_dir)
        rmtree(self.build_dir)
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

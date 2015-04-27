#! /usr/bin/env python
# -*- coding: utf-8 -*-

from collections import OrderedDict
import os
import sys
import re
import codecs
import tempfile
import argparse
import logging
import json
from time import strftime
from subprocess import check_call, check_output, call
from shutil import move, rmtree, copy, copytree
from glob import glob
from logging import info, warning

#import ipdb

class AssetBuilder():
    def __init__(self, target=None, asset_version=None, top_dir=None, user_dir=None, cdn_dir=None, build_dir=None):
        self.target              = target or 'master'
        self.is_master           = self.target == 'master'
        self.asset_version       = asset_version or "%s %s" % (target, strftime('%Y-%m-%d %H:%M:%S'))
        self.asset_version_dir   = 'ver1'   # FIXME
        self_dir                 = os.path.dirname(os.path.abspath(__file__))
        master_dir               = os.path.normpath(self_dir+'/../../box/kms_master_asset')
        self.users_dir           = os.path.normpath(self_dir+'/../../box/users_generated')
        user_dir_default         = re.sub('kms_[^_]+_asset', 'kms_'+target+'_asset', master_dir)
        cdn_dir_default          = '/var/www/cdn'
        self.master_manifest_dir = master_dir+"/manifests"
        self.master_xlsx_dir     = master_dir+'/master'
        self.master_editor_dir   = master_dir+'/editor'

        top_dir_default          = user_dir_default if self.is_master else self.users_dir+"/"+target
        self.top_dir             = top_dir         or top_dir_default
        user_dir                 = user_dir        or user_dir_default
        self.cdn_dir             = cdn_dir         or cdn_dir_default
        self.build_dir           = build_dir       or tempfile.mkdtemp(prefix = 'kms_asset_builder_build')
        self.deply_src_dir       = tempfile.mkdtemp(prefix = 'kms_asset_builder_deploy')
        self.remote_dir_asset    = self.asset_version_dir+'/contents' if self.is_master else self.target + '/contents'
        self.auto_cleanup = not build_dir   # do not clean up when user specified
        
        info("target = %s", self.target)
        info("asset version = '%s'", self.asset_version)
        info("top-dir = %s", self.top_dir)
        info("user-dir = %s", user_dir)
        info("cdn-dir = %s", self.cdn_dir)
        info("build-dir = %s", self.build_dir)

        self.local_asset_search_path = user_dir+'/contents'
        self.user_xlsx_dir           = user_dir+'/master'
        self.user_editor_dir         = user_dir+'/editor'

        user_editor_schema = user_dir+'/editor_schema/editor_schema.json'
        self.editor_schema = user_editor_schema if os.path.exists(user_editor_schema) else master_dir+'/editor_schema/editor_schema.json'

        self.manifest_dir  = self.top_dir+'/manifests'
        self.schema_dir    = self.top_dir+'/master_derivatives'
        self.data_dir      = self.top_dir+'/master_derivatives'
        self.fbs_dir       = self.top_dir+'/master_derivatives'
        self.bin_dir       = self.top_dir+'/contents/master'
        self.header_dir    = self.top_dir+'/master_header'
        self.gd_dir        = self.top_dir+'/glyph_designer/'
        self.font_dir      = self.top_dir+'/contents/files/font'

        self.manifest_bin  = self_dir+'/manifest_generate.py'
        self.xls2json_bin  = self_dir+'/master_data_xls2json.py'
        self.json2fbs_bin  = self_dir+'/json2fbs.py'
        self.flatc_bin     = self_dir+'/flatc'
        self.json2font_bin = self_dir+'/json2font.py'
        
        self.PROJECT_MANIFEST_FILE   = 'dev.project.manifest'
        self.VERSION_MANIFEST_FILE   = 'dev.version.manifest'
        self.REFERENCE_MANIFEST_FILE = 'dev.reference.manifest'
        self.JSON_SCHEMA_FILE        = 'master_schema.json'
        self.JSON_DATA_FILE          = 'master_data.json'
        self.FBS_FILE                = 'master_data.fbs'
        self.BIN_FILE                = 'master_data.bin'
        self.HEADER_FILE             = 'master_data_generated.h'
        self.FBS_ROOT_TYPE           = 'MasterDataFBS'
        self.FBS_NAME_SPACE          = 'kms.fbs'
        self.DEV_CDN_URL             = 'http://kms-dev.dev.gree.jp/cdn'

    # setup dest directories
    def setup_dir(self):
        for path in (self.build_dir, self.local_asset_search_path, self.manifest_dir, self.master_editor_dir, self.user_editor_dir, self.master_xlsx_dir, self.user_xlsx_dir, self.schema_dir, self.data_dir, self.fbs_dir, self.bin_dir, self.header_dir, self.users_dir):
            if not os.path.exists(path):
                os.makedirs(path)

    # get xlsx master data files
    def _get_xlsxes(self):
        xlsx_dirs = (self.master_xlsx_dir, self.user_xlsx_dir)
        xlsxes = {}
        for xlsx_dir in xlsx_dirs:
            for xlsx_path in glob("%s/*.xlsx" % xlsx_dir):
                basename = os.path.basename(xlsx_path)
                if re.match('^~\$', basename):
                    continue
                xlsxes[basename] = xlsx_path
        return xlsxes.values()

    # get editor data files
    def _get_editor_files(self):
        editor_dirs = (self.master_editor_dir, self.user_editor_dir)
        editor_files = {}
        for editor_dir in editor_dirs:
            for editor_path in glob("%s/*.json" % editor_dir):
                basename = os.path.basename(editor_path)
                editor_files[basename] = editor_path
        return editor_files.values()

    # check modification of user editted files
    def _check_modified(self, target, base):
        timestamps = []
        for f in (target, base):
            ts = os.stat(f).st_mtime if os.path.exists(f) else 0
            timestamps.append(ts)
        return timestamps[0] > timestamps[1]

    # create manifest json from
    def build_manifest(self, asset_version=None, src_local_asset_search_path=None, dest_project_manifest=None, dest_version_manifest=None):
        asset_version           = asset_version or self.asset_version
        local_asset_search_path = src_local_asset_search_path or self.local_asset_search_path
        dest_project_manifest   = dest_project_manifest or self.build_dir+'/'+self.PROJECT_MANIFEST_FILE
        dest_version_manifest   = dest_version_manifest or self.build_dir+'/'+self.VERSION_MANIFEST_FILE
        url_asset               = self.DEV_CDN_URL+'/'
        
        if self.is_master:
            reference_manifest    = self.master_manifest_dir+'/'+self.REFERENCE_MANIFEST_FILE
            url_project_manifest  = self.DEV_CDN_URL+'/'+self.asset_version_dir+'/'+self.PROJECT_MANIFEST_FILE
            url_version_manifest  = self.DEV_CDN_URL+'/'+self.VERSION_MANIFEST_FILE
        else:
            reference_manifest    = self.master_manifest_dir+'/'+self.PROJECT_MANIFEST_FILE
            url_project_manifest  = self.DEV_CDN_URL+'/'+self.target+'/'+self.PROJECT_MANIFEST_FILE
            url_version_manifest  = self.DEV_CDN_URL+'/'+self.target+'/'+self.VERSION_MANIFEST_FILE

        info("build manifest: %s -> %s + %s" % (local_asset_search_path, os.path.basename(dest_project_manifest), os.path.basename(dest_version_manifest)))

        cmdline = [self.manifest_bin, dest_project_manifest, dest_version_manifest,
                   asset_version, url_project_manifest, url_version_manifest, url_asset,
                   self.remote_dir_asset, local_asset_search_path, "--ref", reference_manifest]
        check_call(cmdline)
        return True

    # cerate json from xlsx
    def build_json(self, src_xlsxes=None, dest_schema=None, dest_data=None):
        src_xlsxes  = src_xlsxes  or self._get_xlsxes()
        dest_schema = dest_schema or self.build_dir+'/'+self.JSON_SCHEMA_FILE
        dest_data   = dest_data   or self.build_dir+'/'+self.JSON_DATA_FILE
        info("build json: %s + %s" % (os.path.basename(dest_schema), os.path.basename(dest_data)))

        cmdline = [self.xls2json_bin] + src_xlsxes + ['--schema-json', dest_schema, '--data-json', dest_data, '--target', self.target]
        check_call(cmdline)
        return True

    # merge editor's json data into the master json data
    def merge_editor_file(self):
        for master_file, editor_files in ((self.build_dir+'/'+self.JSON_DATA_FILE, self._get_editor_files()), (self.build_dir+'/'+self.JSON_SCHEMA_FILE, [self.editor_schema])):
            with open(master_file, 'r') as f:
                json_data = json.loads(f.read(), object_pairs_hook=OrderedDict)

            for editor_file in editor_files:
                with open(editor_file, 'r') as f:
                    editor_json_data = json.loads(f.read(), object_pairs_hook=OrderedDict)
                for key in editor_json_data:
                    json_data[key] = editor_json_data[key]

            with open(master_file, 'w') as f:
                j = json.dumps(json_data, ensure_ascii = False, indent = 4)
                f.write(j.encode("utf-8"))


    # create fbs from json
    def build_fbs(self, src_json=None, dest_fbs=None, root_type=None, name_space=None):
        src_json   = src_json   or self.build_dir+'/'+self.JSON_SCHEMA_FILE
        dest_fbs   = dest_fbs   or self.build_dir+'/'+self.FBS_FILE
        root_type  = root_type  or self.FBS_ROOT_TYPE
        name_space = name_space or self.FBS_NAME_SPACE
        info("build fbs: %s" % os.path.basename(dest_fbs))

        cmdline = [self.json2fbs_bin, src_json, root_type, name_space]
        with open(dest_fbs, 'w') as fp:
            print >> fp, check_output(cmdline)
        return True

    # create bin+header from json+fbs
    def build_bin(self, src_json=None, src_fbs=None, dest_bin=None, dest_header=None):
        src_json    = src_json    or self.build_dir+'/'+self.JSON_DATA_FILE
        src_fbs     = src_fbs     or self.build_dir+'/'+self.FBS_FILE
        dest_bin    = dest_bin    or self.build_dir+'/'+self.BIN_FILE
        dest_header = dest_header or self.build_dir+'/'+self.HEADER_FILE
        dest_dir    = os.path.dirname(dest_bin)
        info("build bin: %s + %s" % (os.path.basename(dest_bin), os.path.basename(dest_header)))
        if os.path.dirname(dest_bin) != os.path.dirname(dest_header):
            raise Exception("%s and %s must be same dir" % (dest_bin, dest_header))

        cmdline = [self.flatc_bin, '-c', '-b', '-o', dest_dir, src_fbs, src_json]
        check_call(cmdline)
        return True

    # create fnt+png from json
    def build_font(self, src_json=None, src_gd_dir=None, dest_font_dir=None):
        # check GDCL
        if call(['GDCL'], stdout = open(os.devnull, 'w')) == 127:
            warning("GDCL is not installed. skip to build font")
            return False

        # build font by GDCL
        src_json      = src_json      or self.build_dir+'/'+self.JSON_DATA_FILE
        src_gd_dir    = src_gd_dir    or self.gd_dir
        dest_font_dir = dest_font_dir or self.build_dir
        cmdline = [self.json2font_bin, src_json, src_gd_dir, dest_font_dir]
        check_call(cmdline)
        return True

    # copy all generated files 
    def install(self, build_dir=None):
        build_dir = build_dir or self.build_dir
        list = [
            (build_dir+'/'+self.PROJECT_MANIFEST_FILE, self.manifest_dir+'/'+self.PROJECT_MANIFEST_FILE),
            (build_dir+'/'+self.VERSION_MANIFEST_FILE, self.manifest_dir+'/'+self.VERSION_MANIFEST_FILE),
            (build_dir+'/'+self.JSON_SCHEMA_FILE,      self.schema_dir+'/'+self.JSON_SCHEMA_FILE),
            (build_dir+'/'+self.JSON_DATA_FILE,        self.data_dir+'/'+self.JSON_DATA_FILE),
            (build_dir+'/'+self.FBS_FILE,              self.fbs_dir+'/'+self.FBS_FILE),
            (build_dir+'/'+self.BIN_FILE,              self.bin_dir+'/'+self.BIN_FILE),
            (build_dir+'/'+self.HEADER_FILE,           self.header_dir+'/'+self.HEADER_FILE)
        ]
        for font_path in glob("%s/*.fnt" % build_dir):
            png_path = re.sub('.fnt$', '.png', font_path)
            list.append((font_path, self.font_dir+'/'+os.path.basename(font_path)))
            list.append((png_path,  self.font_dir+'/'+os.path.basename(png_path)))
        for src, dest in list:
            if os.path.exists(src):
                info("install: %s -> %s" % (os.path.basename(src), os.path.dirname(dest)))
                if os.path.exists(dest):
                    os.remove(dest)
                move(src, dest)
        return True

    def deploy_dev(self):
        project_file = self.manifest_dir+'/'+self.PROJECT_MANIFEST_FILE
        version_file = self.manifest_dir+'/'+self.VERSION_MANIFEST_FILE
        rsync = ['rsync', '-crltvO']

        dst_dir = self.cdn_dir+'/'+self.asset_version_dir if self.is_master else self.cdn_dir+'/'+self.target
        if not os.path.exists(dst_dir):
            os.makedirs(dst_dir)
        dst_asset = dst_dir+'/contents'
        dst_project_manifest  = dst_dir+'/'+self.PROJECT_MANIFEST_FILE
        dst_listfile = self.cdn_dir+"dev.asset_list.json"

        if self.is_master:
            dst_version_manifest = self.cdn_dir+self.VERSION_MANIFEST_FILE
            manifest = {}
            with open(project_file, 'r') as f:
                manifest = json.load(f)
            assets = manifest.get('assets')
            for key in assets:
                asset = assets.get(key)
                path = asset.get('path')
                if path == self.remote_dir_asset+"/"+key:
                    (path, name)  = os.path.split(self.deply_src_dir+"/"+key)
                    if not os.path.exists(path):
                        os.makedirs(path)
                    copy(self.local_asset_search_path + "/"+ key, self.deply_src_dir + "/"+key)
        else:
            dst_version_manifest = dst_dir+"/"+self.VERSION_MANIFEST_FILE
            copytree(self.local_asset_search_path+"/files", self.deply_src_dir+"/files")
            copytree(self.bin_dir, self.deply_src_dir+"/master")

        usernames = []
        for f in os.listdir(self.users_dir) :
            if os.path.isdir(self.users_dir+"/"+f):
                usernames +=[f]

        list_file = self.build_dir + "/deploy_files.json"
        with open(list_file, 'w') as f:
            json.dump(usernames, f, sort_keys=True, indent=2)
        os.chmod(list_file, 0664)
        check_call(rsync + [list_file, dst_listfile])
        check_call("find " + self.deply_src_dir + " -type f -print | xargs chmod 664", shell=True)
        check_call("find " + self.deply_src_dir + " -type d -print | xargs chmod 775", shell=True)
        check_call(rsync + ['--delete', self.deply_src_dir+"/", dst_asset])
        check_call(['chmod', '775', dst_dir+"/contents"])
        check_call(rsync + [version_file, dst_version_manifest])
        check_call(rsync + [project_file, dst_project_manifest])

    # do all processes
    def build_all(self, check_modified=True):
        # check modified
        build_depends = self._get_xlsxes() + self._get_editor_files() + [ self.editor_schema ]
        modified = False
        if check_modified:
            for src in build_depends:
                if self._check_modified(src, self.bin_dir+'/'+self.BIN_FILE):
                    modified = True
                    break
            if not modified:
                info("xlsxes and editor data are not modified")

        # main process
        try:
            self.setup_dir()
            if not check_modified or modified:
                self.build_json()
                self.merge_editor_file()
                self.build_fbs()
                self.build_bin()
                self.build_font()
            self.build_manifest()
            self.install()
            self.deploy_dev()
        finally:
            if self.auto_cleanup:
                self.cleanup()
        return True

    # clean up
    def cleanup(self):
        rmtree(self.build_dir)
        rmtree(self.deply_src_dir)
        return True

if __name__ == '__main__':
    sys.stdout = codecs.lookup('utf_8')[-1](sys.stdout)
    logging.basicConfig(level = logging.INFO, format = '%(asctime)-15s %(levelname)s %(message)s')

    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawTextHelpFormatter,
        description = 'build asset and master data', 
        epilog = """\
commands:
  build              do all build processes
  build-all          same as 'build'
  build-manifest     generate project.manifest + version.manifest from contents/**
  build-json         generate master_data.json + master_schema.json from master_data.xlsx
  build-fbs          generate master_data.fbs from master_data.json
  build-bin          generate master_data.bin + master_header/*.h from master_data.json + master_data.fbs
  build-font         generate bitmap font from master_data.json
  deploy-dev         deploy asset files to cdn directory
  install            install files from build dir
  cleanup            cleanup build dir

examples:
  build all for 'kms_master_data'
    $ cd kms_master_data/hook
    $ ./build.py build

  build all for 'kms_xxx.yyy_asset'
    $ kms_master_asset/hook/build.py build --target xxx.yyy

  build only fbs
    $ cd kms_master_asset/hook
    $ ./build.py build-fbs --build-dir /tmp/asset_builder
    $ ./build.py install --build-dir /tmp/asset_builder
    $ ./build.py cleanup --build-dir /tmp/asset_builder
        """)
    parser.add_argument('command',     help = 'build command (build|build-manifest|build-json|build-fbs|build-bin|install|deploy-dev|cleanup)')
    parser.add_argument('--target', default = 'master', help = 'target name (e.g. master, kiyoto.suzuki, ...) default: master')
    parser.add_argument('--force',  default = False, action = 'store_true', help = 'skip check timestamp. always build')
    parser.add_argument('--asset-version', help = 'asset version. default: <target>.<unix-timestamp>')
    parser.add_argument('--top-dir',       help = 'asset top directory. default: same as script top')
    parser.add_argument('--user-dir',      help = 'user working directory top. default: same as script top')
    parser.add_argument('--build-dir',     help = 'build directory. default: temp dir')
    args = parser.parse_args()

    asset_builder = AssetBuilder(target = args.target, asset_version = args.asset_version, top_dir = args.top_dir, user_dir = args.user_dir, build_dir = args.build_dir)
    if args.command in ('build', 'build-all'):
        asset_builder.build_all(not args.force)
    elif args.command == 'build-manifest':
        asset_builder.build_manifest()
    elif args.command == 'build-json':
        asset_builder.build_json()
    elif args.command == 'build-fbs':
        asset_builder.build_fbs()
    elif args.command == 'build-bin':
        asset_builder.build_bin()
    elif args.command == 'build-font':
        asset_builder.build_font()
    elif args.command == 'install':
        asset_builder.install()
    elif args.command == 'deploy-dev':
        asset_builder.deploy_dev()
    elif args.command == 'cleanup':
        asset_builder.cleanup()
    exit(0)

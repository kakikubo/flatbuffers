#! /usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import re
import codecs
import tempfile
import argparse
import logging
import json
from time import strftime
from subprocess import check_call, check_output
from shutil import move, rmtree, copy
from glob import glob
from logging import info

#import ipdb
DEV_URL = 'http://tmp-kiyoto-suzuki-ffl.gree-dev.net/cdn'
DEV_HOST = 'ubuntu@10.1.1.24'
DEV_CDN_ROOT = '/var/www/cdn/'
DEV_SSH_KEY = '/Users/ffl.jenkins/.ssh/id_rsa.openstack'

MASTER_LATEST_DIR = 'ver1'

class AssetBuilder():
    def __init__(self, target=None, asset_version=None, top_dir=None, user_dir=None, build_dir=None):
        self_dir = os.path.dirname(os.path.abspath(__file__))
        self.target = target or 'master'
        self.asset_version   = asset_version   or "%s %s" % (target, strftime('%Y-%m-%d %H:%M:%S'))
        master_dir      = os.path.normpath(self_dir+'/../../box/kms_master_asset')
        user_dir_default     = re.sub('kms_[^_]+_asset', 'kms_'+target+'_asset', master_dir)
        self.master_manifest_dir = master_dir + "/manifest"
        top_dir_default      = user_dir_default if self.target == 'master' else 'generated/'+user_dir_default
        self.top_dir         = top_dir         or top_dir_default
        self.user_dir        = user_dir        or user_dir_default
        self.build_dir       = build_dir       or tempfile.mkdtemp(prefix = 'kms_asset_builder')
        self.remote_dir_asset = MASTER_LATEST_DIR + '/contents' if self.target == 'master' else self.target + '/contents'
        
        info("target = %s", self.target)
        info("asset version = '%s'", self.asset_version)
        info("top-dir = %s", self.top_dir)
        info("user-dir = %s", self.user_dir)
        info("build-dir = %s", self.build_dir)

        self.local_asset_search_path = self.user_dir+'/contents'
        self.manifest_dir  = self.top_dir+'/manifests'
        self.xlsx_dir      = self.top_dir+'/master'
        self.user_xlsx_dir = self.user_dir+'/master'
        self.schema_dir    = self.top_dir+'/master_derivatives'
        self.data_dir      = self.top_dir+'/master_derivatives'
        self.fbs_dir       = self.top_dir+'/master_derivatives'
        self.bin_dir       = self.top_dir+'/contents/master'
        self.header_dir    = self.top_dir+'/master_header'

        self.manifest_bin = self_dir+'/manifest_generate.py'
        self.xls2json_bin = self_dir+'/master_data_xls2json.py'
        self.json2fbs_bin = self_dir+'/json2fbs.py'
        self.flatc_bin    = self_dir+'/flatc'
        
        self.PROJECT_MANIFEST_FILE = 'dev.project.manifest'
        self.VERSION_MANIFEST_FILE = 'dev.version.manifest'
        self.REFERENCE_MANIFEST_FILE = 'dev.reference.manifest'
        self.JSON_SCHEMA_FILE      = 'master_schema.json'
        self.JSON_DATA_FILE        = 'master_data.json'
        self.FBS_FILE              = 'master_data.fbs'
        self.BIN_FILE              = 'master_data.bin'
        self.HEADER_FILE           = 'master_data_generated.h'
        self.FBS_ROOT_TYPE         = 'MasterDataFBS'
        self.FBS_NAME_SPACE        = 'kms.fbs'

    # setup dest directories
    def setup_dir(self):
        for path in (self.build_dir, self.local_asset_search_path, self.manifest_dir, self.xlsx_dir, self.user_xlsx_dir, self.schema_dir, self.data_dir, self.fbs_dir, self.bin_dir, self.header_dir):
            if not os.path.exists(path):
                os.makedirs(path)

    # get xlsx master data files
    def _get_xlsxes(self, xlsx_dirs=None):
        xlsx_dirs = xlsx_dirs or (self.xlsx_dir, self.user_xlsx_dir)
        xlsxes = []
        for xlsx_dir in xlsx_dirs:
            for xlsx_path in glob("%s/*.xlsx" % xlsx_dir):
                if (re.match('^~\$', os.path.basename(xlsx_path))):
                    continue
                xlsxes.append(xlsx_path)
        return xlsxes

    # check modification of user editted files
    def _check_modified(self, target, base):
        timestamps = []
        for f in (target, base):
            ts = os.stat(f).st_mtime if os.path.exists(f) else 0
            timestamps.append(ts)
        return timestamps[0] > timestamps[1]

    # create manifest json from
    def build_manifest(self, asset_version=None, src_local_asset_search_path=None, dest_project_manifest=None, dest_version_manifest=None):
        asset_version         = asset_version or self.asset_version
        local_asset_search_path         = src_local_asset_search_path or self.local_asset_search_path
        dest_project_manifest = dest_project_manifest or self.build_dir+'/'+self.PROJECT_MANIFEST_FILE
        dest_version_manifest = dest_version_manifest or self.build_dir+'/'+self.VERSION_MANIFEST_FILE
        url_asset             = DEV_URL + '/'
        
        if self.target == 'master':
            reference_manifest    = self.master_manifest_dir+'/'+self.REFERENCE_MANIFEST_FILE
            url_project_manifest  = DEV_URL + '/' + MASTER_LATEST_DIR+'/'+self.PROJECT_MANIFEST_FILE
            url_version_manifest  = DEV_URL + '/' + MASTER_LATEST_DIR+'/'+self.VERSION_MANIFEST_FILE
        else:
            reference_manifest    = self.master_manifest_dir+'/'+self.PROJECT_MANIFEST_FILE
            url_project_manifest  = DEV_URL + '/' + self.target+'/'+self.PROJECT_MANIFEST_FILE
            url_version_manifest  = DEV_URL + '/' + self.target+'/'+self.VERSION_MANIFEST_FILE

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

    # create fbs from json
    def build_fbs(self, src_json=None, dest_fbs=None, root_type=None, name_space=None):
        src_json   = src_json   or self.build_dir+'/'+self.JSON_DATA_FILE
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

    # copy all generated files 
    def install(self, build_dir=None):
        build_dir = build_dir or self.build_dir
        list = (
            (build_dir+'/'+self.PROJECT_MANIFEST_FILE, self.manifest_dir+'/'+self.PROJECT_MANIFEST_FILE),
            (build_dir+'/'+self.VERSION_MANIFEST_FILE, self.manifest_dir+'/'+self.VERSION_MANIFEST_FILE),
            (build_dir+'/'+self.JSON_SCHEMA_FILE,      self.schema_dir+'/'+self.JSON_SCHEMA_FILE),
            (build_dir+'/'+self.JSON_DATA_FILE,        self.data_dir+'/'+self.JSON_DATA_FILE),
            (build_dir+'/'+self.FBS_FILE,              self.fbs_dir+'/'+self.FBS_FILE),
            (build_dir+'/'+self.BIN_FILE,              self.bin_dir+'/'+self.BIN_FILE),
            (build_dir+'/'+self.HEADER_FILE,           self.header_dir+'/'+self.HEADER_FILE)
        )
        for pair in list:
            if os.path.exists(pair[0]):
                info("install: %s -> %s" % (os.path.basename(pair[0]), os.path.dirname(pair[1])))
                if os.path.exists(pair[1]):
                    os.remove(pair[1])
                move(pair[0], pair[1])
        return True

    def deploy_dev(self):
        project_file          = self.manifest_dir+'/'+self.PROJECT_MANIFEST_FILE
        version_file          = self.manifest_dir+'/'+self.VERSION_MANIFEST_FILE
        
        dst_dir = DEV_CDN_ROOT+MASTER_LATEST_DIR
        dst_asset = DEV_HOST+':'+dst_dir+'/contents'
        dst_project_manifest  = DEV_HOST+':'+dst_dir+'/'+self.PROJECT_MANIFEST_FILE
        dst_version_manifest  = DEV_HOST+':'+dst_dir+'/'+self.VERSION_MANIFEST_FILE
        dst_top_manifest      = DEV_HOST+':'+DEV_CDN_ROOT+self.VERSION_MANIFEST_FILE
        
        check_call(['ssh', '-i', DEV_SSH_KEY, DEV_HOST, 'mkdir', '-p', dst_dir])
        rsync = ['rsync', '-a', '-e', "ssh -i "+DEV_SSH_KEY]
        manifest = {}
        with open(project_file, 'r') as f:
            manifest = json.load(f)
    
        try:
            tmp = tempfile.mkdtemp(prefix = 'kms_asset_builder_contents')
            
            assets = manifest.get('assets')
            for key in assets:
                asset = assets.get(key)
                path = asset.get('path')
                if path == self.remote_dir_asset+"/"+key:
                    (path, name)  = os.path.split(tmp+"/"+key)
                    if not os.path.exists(path):
                        os.makedirs(path)
                    copy(self.local_asset_search_path + "/"+ key, tmp + "/"+key)
            check_call(rsync + ['--delete', tmp+"/", dst_asset])
        finally:
            rmtree(tmp)
        
        check_call(rsync + [version_file, dst_top_manifest])
        check_call(rsync + [version_file, dst_version_manifest])
        check_call(rsync + [project_file, dst_project_manifest])

    # do all processes
    def build_all(self, check_modified=True):
        # check modified
        xlsxes = self._get_xlsxes()
        modified = False
        if check_modified:
            for xlsx in xlsxes:
                if self._check_modified(xlsx, self.data_dir+'/'+self.JSON_DATA_FILE):
                    modified = True
                    break
            if not modified:
                info("xlsxes are not modified")

        # main process
        try:
            self.setup_dir()
            self.build_manifest()
            if not check_modified or modified:
                self.build_json(xlsxes)
                self.build_fbs()
                self.build_bin()
            self.install()
            self.deploy_dev()
        finally:
            self.cleanup()
        return True

    # clean up
    def cleanup(self):
        rmtree(self.build_dir)
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
    parser.add_argument('command',     help = 'build command (build|build-manifest|build-json|build-fbs|build-bin|install|cleanup)')
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
    elif args.command == 'install':
        asset_builder.install()
    elif args.command == 'cleanup':
        asset_builder.cleanup()
    exit(0)

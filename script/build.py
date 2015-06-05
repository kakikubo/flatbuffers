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
import logging
from time import strftime
from subprocess import check_call, check_output, call
from shutil import move, rmtree, copy, copytree
from glob import glob
from logging import info, warning, debug

class AssetBuilder():
    def __init__(self, target=None, asset_version=None, main_dir=None, master_dir=None, build_dir=None, cdn_dir=None, git_dir=None):
        self.target              = target or 'master'
        self.is_master           = self.target == 'master'

        self.asset_version       = asset_version or "%s %s" % (target, strftime('%Y-%m-%d %H:%M:%S'))
        self.asset_version_dir   = 'ver1' if self.is_master else target

        self_dir = os.path.dirname(os.path.abspath(__file__))
        for main_dir_default in (\
            os.path.normpath(os.curdir+'/kms_'+target+'_asset'), \
            os.path.normpath(self_dir+'/../../box/kms_'+target+'_asset'), \
            os.path.normpath(os.path.expanduser('~/Box Sync/kms_'+target+'_asset'))):
            if os.path.exists(main_dir_default):
                break
        self.org_main_dir = main_dir or main_dir_default

        for master_dir_default in (\
            os.path.normpath(os.curdir+'/kms_master_asset'), \
            os.path.normpath(self_dir+'/../../box/kms_master_asset'), \
            os.path.normpath(os.path.expanduser('~/Box Sync/kms_master_asset'))):
            if os.path.exists(master_dir_default):
                break
        self.org_master_dir = master_dir or master_dir_default

        cdn_dir_default          = '/var/www/cdn'
        self.cdn_dir             = cdn_dir   or cdn_dir_default
        self.git_dir             = git_dir
        self.build_dir           = build_dir or tempfile.mkdtemp(prefix = 'kms_asset_builder_build_')
        self.main_dir            = self.build_dir+'/main'
        self.master_dir          = self.build_dir+'/master'
        self.remote_dir_asset    = self.asset_version_dir+'/contents' if self.is_master else self.target + '/contents'
        self.auto_cleanup        = not self.build_dir   # do not clean up when user specified

        if not os.path.exists(self.build_dir):
            os.makedirs(self.build_dir)
        # isolate from modefation via box
        self.prepare_dir(self.org_main_dir, self.main_dir)
        if self.org_main_dir == self.org_master_dir:
            self.master_dir = self.main_dir
        else:
            self.prepare_dir(self.org_master_dir, self.master_dir)
        
        info("target = %s", self.target)
        info("asset version = '%s'", self.asset_version)
        info("main-dir = %s", main_dir)
        info("master-dir = %s", master_dir)
        info("build-dir = %s", self.build_dir)
        info("cdn-dir = %s", self.cdn_dir)
        info("git-dir = %s", self.git_dir)
        info("remote-dir-asset = %s", self.remote_dir_asset)

        self.manifest_dir             = self.main_dir+'/manifests'
        self.master_schema_dir        = self.main_dir+'/master_derivatives'
        self.master_data_dir          = self.main_dir+'/master_derivatives'
        self.master_fbs_dir           = self.main_dir+'/master_derivatives'
        self.master_bin_dir           = self.main_dir+'/contents/master'
        self.master_header_dir        = self.main_dir+'/master_header'
        self.main_header_dir          = self.main_dir+'/user_header'
        self.font_dir                 = self.main_dir+'/contents/files/font'

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

        main_editor_schema = self.main_editor_schema_dir+'/editor_schema.json'
        self.editor_schema = main_editor_schema if os.path.exists(main_editor_schema) else self.master_editor_schema_dir+'/editor_schema.json'

        self.manifest_bin  = self_dir+'/manifest_generate.py'
        self.xls2json_bin  = self_dir+'/master_data_xls2json.py'
        self.json2fbs_bin  = self_dir+'/json2fbs.py'
        self.flatc_bin     = self_dir+'/flatc'
        self.fbs2class_bin = self_dir+'/fbs2class.py'
        self.json2font_bin = self_dir+'/json2font.py'
        
        self.PROJECT_MANIFEST_FILE   = 'dev.project.manifest'
        self.VERSION_MANIFEST_FILE   = 'dev.version.manifest'
        self.REFERENCE_MANIFEST_FILE = 'dev.reference.manifest'
        self.MASTER_JSON_SCHEMA_FILE = 'master_schema.json'
        self.MASTER_JSON_DATA_FILE   = 'master_data.json'
        self.MASTER_FBS_FILE         = 'master_data.fbs'
        self.MASTER_BIN_FILE         = 'master_data.bin'
        self.MASTER_HEADER_FILE      = 'master_data_generated.h'
        self.MASTER_FBS_ROOT_NAME    = 'MasterDataFBS'
        self.MASTER_FBS_NAMESPACE    = 'kms.masterdata'
        self.USER_FBS_FILE           = 'user_data.fbs'
        self.USER_CLASS_FILE         = 'user_data.h'
        self.USER_HEADER_FILE        = 'user_data_generated.h'
        self.USER_FBS_ROOT_NAME      = 'UserDataFBS'
        self.USER_FBS_NAMESPACE      = 'kms.userdata'
        self.DEV_CDN_URL             = 'http://kms-dev.dev.gree.jp/cdn' # FIXME

    # prepare and isolate source data via box
    def prepare_dir(self, src, dest):
        if  os.path.exists(dest):
            rmtree(dest)
        info("copytree '%s' -> '%s'" % (src, dest))
        copytree(src, dest)

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
            self.main_header_dir):
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

    # get editor data files
    def _get_editor_files(self):
        editor_dirs = (self.master_editor_dir, self.main_editor_dir)
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
    def build_manifest(self, asset_version=None, dest_project_manifest=None, dest_version_manifest=None):
        asset_version           = asset_version or self.asset_version
        dest_project_manifest   = dest_project_manifest or self.manifest_dir+'/'+self.PROJECT_MANIFEST_FILE
        dest_version_manifest   = dest_version_manifest or self.manifest_dir+'/'+self.VERSION_MANIFEST_FILE
        url_asset               = self.DEV_CDN_URL+'/'
        
        reference_manifest    = self.master_manifest_dir+'/'+self.REFERENCE_MANIFEST_FILE
        url_project_manifest  = self.DEV_CDN_URL+'/'+self.asset_version_dir+'/'+self.PROJECT_MANIFEST_FILE
        if self.is_master:
            url_version_manifest  = self.DEV_CDN_URL+'/'+self.VERSION_MANIFEST_FILE
        else:
            url_version_manifest  = self.DEV_CDN_URL+'/'+self.asset_version_dir+'/'+self.VERSION_MANIFEST_FILE

        info("build manifest: %s + %s" % (os.path.basename(dest_project_manifest), os.path.basename(dest_version_manifest)))

        cmdline = [self.manifest_bin, dest_project_manifest, dest_version_manifest,
                   asset_version, url_project_manifest, url_version_manifest, url_asset,
                   self.remote_dir_asset, self.main_dir+'/contents', "--ref", reference_manifest]
        debug(' '.join(cmdline))
        check_call(cmdline)
        return True

    # cerate master data json from xlsx
    def build_master_json(self, src_xlsxes=None, dest_schema=None, dest_data=None):
        src_xlsxes  = src_xlsxes  or self._get_xlsxes()
        dest_schema = dest_schema or self.build_dir+'/'+self.MASTER_JSON_SCHEMA_FILE
        dest_data   = dest_data   or self.build_dir+'/'+self.MASTER_JSON_DATA_FILE
        info("build master json: %s + %s" % (os.path.basename(dest_schema), os.path.basename(dest_data)))

        cmdline = [self.xls2json_bin] + src_xlsxes + ['--schema-json', dest_schema, '--data-json', dest_data]
        debug(' '.join(cmdline))
        check_call(cmdline)
        return True

    # merge editor's json data into the master json data
    def merge_editor_file(self):

        for master_file, editor_files in ((self.build_dir+'/'+self.MASTER_JSON_DATA_FILE, self._get_editor_files()), (self.build_dir+'/'+self.MASTER_JSON_SCHEMA_FILE, [self.editor_schema])):
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

    # create bin+header from json+fbs
    def build_master_bin(self, src_json=None, src_fbs=None, dest_bin=None, dest_header=None):
        src_json    = src_json    or self.build_dir+'/'+self.MASTER_JSON_DATA_FILE
        src_fbs     = src_fbs     or self.build_dir+'/'+self.MASTER_FBS_FILE
        dest_bin    = dest_bin    or self.build_dir+'/'+self.MASTER_BIN_FILE
        dest_header = dest_header or self.build_dir+'/'+self.MASTER_HEADER_FILE
        main_dir    = os.path.dirname(dest_bin)
        info("build master bin: %s + %s" % (os.path.basename(dest_bin), os.path.basename(dest_header)))
        if os.path.dirname(dest_bin) != os.path.dirname(dest_header):
            raise Exception("%s and %s must be same dir" % (dest_bin, dest_header))

        cmdline = [self.flatc_bin, '-c', '-b', '-o', main_dir, src_fbs, src_json]
        debug(' '.join(cmdline))
        check_call(cmdline)
        return True

    # create class header from fbs
    def build_user_class(self, src_fbs=None, dest_class=None, namespace=None):
        src_fbs    = src_fbs    or self.main_schema_dir+'/'+self.USER_FBS_FILE
        dest_class = dest_class or self.build_dir+'/'+self.USER_CLASS_FILE
        namespace  = namespace  or self.USER_FBS_NAMESPACE
        if not os.path.exists(src_fbs):
            return False

        info("build user class: %s" % os.path.basename(dest_class))
        cmdline = [self.fbs2class_bin, src_fbs, dest_class, '--namespace', namespace]
        debug(' '.join(cmdline))
        check_call(cmdline)
        return True

    # create bin+header from json+fbs
    def build_user_header(self, src_json=None, src_fbs=None, dest_bin=None, dest_header=None):
        src_fbs     = src_fbs     or self.main_schema_dir+'/'+self.USER_FBS_FILE
        dest_header = dest_header or self.build_dir+'/'+self.USER_HEADER_FILE
        main_dir    = os.path.dirname(dest_header)
        info("build user header: %s" % os.path.basename(dest_header))

        cmdline = [self.flatc_bin, '-c', '-o', main_dir, src_fbs]
        debug(' '.join(cmdline))
        check_call(cmdline)
        return True

    # create fnt+png from json
    def build_font(self, src_json=None, src_gd_dir=None, dest_font_dir=None):
        # check GDCL
        if call(['GDCL'], stdout = open(os.devnull, 'w')) == 127:
            warning("GDCL is not installed. skip to build font")
            return False

        # build font by GDCL
        src_json      = src_json      or self.build_dir+'/'+self.MASTER_JSON_DATA_FILE
        src_gd_dir    = src_gd_dir    or self.master_gd_dir
        dest_font_dir = dest_font_dir or self.build_dir
        cmdline = [self.json2font_bin, src_json, src_gd_dir, dest_font_dir]
        debug(' '.join(cmdline))
        check_call(cmdline)
        return True

    # copy all generated files 
    def install(self, build_dir=None):
        build_dir = build_dir or self.build_dir
        list = [
            (build_dir+'/'+self.MASTER_JSON_SCHEMA_FILE, self.master_schema_dir+'/'+self.MASTER_JSON_SCHEMA_FILE),
            (build_dir+'/'+self.MASTER_JSON_DATA_FILE,   self.master_data_dir+'/'+self.MASTER_JSON_DATA_FILE),
            (build_dir+'/'+self.MASTER_FBS_FILE,         self.master_fbs_dir+'/'+self.MASTER_FBS_FILE),
            (build_dir+'/'+self.MASTER_BIN_FILE,         self.master_bin_dir+'/'+self.MASTER_BIN_FILE),
            (build_dir+'/'+self.MASTER_HEADER_FILE,      self.master_header_dir+'/'+self.MASTER_HEADER_FILE),
            (build_dir+'/'+self.USER_CLASS_FILE,         self.main_header_dir+'/'+self.USER_CLASS_FILE),
            (build_dir+'/'+self.USER_HEADER_FILE,        self.main_header_dir+'/'+self.USER_HEADER_FILE)
        ]
        for font_path in glob("%s/*.fnt" % build_dir):
            png_path = re.sub('.fnt$', '.png', font_path)
            list.append((font_path, self.font_dir+'/'+os.path.basename(font_path)))
            list.append((png_path,  self.font_dir+'/'+os.path.basename(png_path)))
        for src, dest in list:
            if os.path.exists(src):
                info("install: %s -> %s" % (os.path.basename(src), os.path.dirname(dest)))
                if not os.path.exists(os.path.dirname(dest)):
                    os.makedirs(os.path.dirname(dest))
                if call(['cmp', '--quiet', src, dest]) == 0:
                    continue
                if os.path.exists(dest):
                    os.remove(dest)
                debug("move '%s' -> '%s'" % (src, dest))
                move(src, dest)
        return True

    def deploy_dev_cdn(self):
        list_file = self.cdn_dir+"/dev.asset_list.json"
        with open(list_file, 'a+') as f:
            f.seek(0)
            usernames = json.load(f)
            if not self.target in usernames and self.target != 'master':
                usernames.append(self.target)
            info("available users = "+", ".join(usernames))
            f.truncate(0)
            json.dump(usernames, f, sort_keys=True, indent=2)
        os.chmod(list_file, 0664)

        project_file = self.manifest_dir+'/'+self.PROJECT_MANIFEST_FILE
        version_file = self.manifest_dir+'/'+self.VERSION_MANIFEST_FILE

        with open(project_file, 'r') as f:
            manifest = json.load(f)
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
                    os.remove(root+'/'+file)

        rsync = ['rsync', '-crltvO']
        #rsync = ['rsync', '-crltvO', '-e', "ssh -i "+DEV_SSH_KEY]
        rsync.extend(['--exclude', '.DS_Store'])

        dest_dir = self.cdn_dir+'/'+self.asset_version_dir
        if not os.path.exists(dest_dir):
            os.makedirs(dest_dir)
        info("deploy to dev cdn: %s -> %s: " % (self.main_dir, dest_dir))

        if self.is_master:
            dest_version_manifest = self.cdn_dir+'/'+self.VERSION_MANIFEST_FILE
        else:
            dest_version_manifest = dest_dir+"/"+self.VERSION_MANIFEST_FILE

        check_call("find " + self.main_dir+'/contents' + " -type f -print | xargs chmod 664", shell=True)
        check_call("find " + self.main_dir+'/contents' + " -type d -print | xargs chmod 775", shell=True)
        check_call(rsync + ['--delete', self.main_dir+'/contents/', dest_dir+'/contents'])
        check_call(['chmod', '775', dest_dir+"/contents"])
        check_call(rsync + [version_file, dest_version_manifest])
        check_call(rsync + [project_file, dest_dir+'/'+self.PROJECT_MANIFEST_FILE])

    def deploy_git_repo(self):
        if not self.is_master or not self.git_dir:
            return

        info("deploy to git repo: %s -> %s" % (self.main_dir, self.git_dir))
        cmdline = ['rsync', '-a', '--exclude', '.DS_Store', '--delete', self.main_dir+'/', self.git_dir]
        debug(' '.join(cmdline))
        check_call(cmdline)

    # do all processes
    def build_all(self, check_modified=True):
        # check modified
        build_depends = self._get_xlsxes() + self._get_editor_files() + [ self.editor_schema, self.main_schema_dir+'/'+self.USER_FBS_FILE ]
        modified = False
        if check_modified:
            timestamp_base_file = self.master_bin_dir+'/'+self.MASTER_BIN_FILE
            for src in build_depends:
                if self._check_modified(src, timestamp_base_file):
                    modified = True
                    break
            if not modified:
                info("source files of auto generated data are not modified")

        # main process
        try:
            self.setup_dir()
            if not check_modified or modified:
                self.build_master_json()
                self.merge_editor_file()
                self.build_master_fbs()
                self.build_master_bin()
                self.build_font()
                self.build_user_class()
                self.install()
            self.build_manifest()
            self.deploy_dev_cdn()
            self.deploy_git_repo()
        finally:
            if self.auto_cleanup:
                self.cleanup()
        return True

    # clean up
    def cleanup(self):
        rmtree(self.build_dir)
        return True

if __name__ == '__main__':
    sys.stdout = codecs.lookup('utf_8')[-1](sys.stdout)
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawTextHelpFormatter,
        description = 'build asset and master data', 
        epilog = """\
commands:
  build              do all build processes
  build-all          same as 'build'
  build-manifest     generate project.manifest + version.manifest from contents/**
  build-json         generate master_data.json + master_schema.json from master_data.xlsx
  build-master-fbs   generate master_data.fbs from master_data.json
  build-master-bin   generate master_data.bin + master_header/*.h from master_data.json + master_data.fbs
  build-user-class   generate user_header/*.h from user_data.fbs
  build-user-header  generate user_header/*_generated.h from user_data.fbs
  build-font         generate bitmap font from master_data.json
  deploy-dev         deploy asset files to cdn directory
  install            install files from build dir
  cleanup            cleanup build dir

examples:
  build all for 'kms_master_data'
    $ cd kms_master_data/hook
    $ ./build.py build

  build on local (for development)
    $ kms_master_asset/hook/build.py build --target master --build-dir build --cdn-dir cdn --log-level DEBUG

  build all for 'kms_xxx.yyy_asset'
    $ kms_master_asset/hook/build.py build --target xxx.yyy

  build only fbs
    $ cd kms_master_asset/hook
    $ ./build.py build-fbs --build-dir /tmp/asset_builder
    $ ./build.py install --build-dir /tmp/asset_builder
    $ ./build.py cleanup --build-dir /tmp/asset_builder
        """)
    parser.add_argument('command',         help = 'build command (build|build-manifest|build-master-json|build-master-fbs|build-master-bin|build-user-class|build-user-header|install|deploy-dev|cleanup)')
    parser.add_argument('--target', default = 'master', help = 'target name (e.g. master, kiyoto.suzuki, ...) default: master')
    parser.add_argument('--force',  default = False, action = 'store_true', help = 'skip check timestamp. always build')
    parser.add_argument('--asset-version', help = 'asset version. default: <target>.<unix-timestamp>')
    parser.add_argument('--master-dir',    help = 'master asset directory. default: same as script top')
    parser.add_argument('--main-dir',      help = 'asset generated directory. default: same as script top')
    parser.add_argument('--build-dir',     help = 'build directory. default: temp dir')
    parser.add_argument('--cdn-dir',       help = 'cdn directory to deploy. default: /var/www/cdn')
    parser.add_argument('--git-dir',       help = 'git directory to deploy. default: (not to deploy)')
    parser.add_argument('--log-level',     help = 'log level (WARNING|INFO|DEBUG). default: INFO')
    args = parser.parse_args()
    logging.basicConfig(level = args.log_level or "INFO", format = '%(asctime)-15s %(levelname)s %(message)s')

    asset_builder = AssetBuilder(target = args.target, asset_version = args.asset_version, main_dir = args.main_dir, master_dir = args.master_dir, build_dir = args.build_dir, cdn_dir = args.cdn_dir, git_dir = args.git_dir)
    if args.command in ('build', 'build-all'):
        asset_builder.build_all(not args.force)
    elif args.command == 'build-manifest':
        asset_builder.build_manifest()
    elif args.command == 'build-master-json':
        asset_builder.build_master_json()
    elif args.command == 'build-master-fbs':
        asset_builder.build_master_fbs()
    elif args.command == 'build-master-bin':
        asset_builder.build_master_bin()
    elif args.command == 'build-user-class':
        asset_builder.build_user_class()
    elif args.command == 'build-user-header':
        asset_builder.build_user_header()
    elif args.command == 'build-font':
        asset_builder.build_font()
    elif args.command == 'install':
        asset_builder.install()
    elif args.command == 'deploy-dev':
        asset_builder.deploy_dev()
    elif args.command == 'cleanup':
        asset_builder.cleanup()
    exit(0)

#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""Update webview assets"""

import os
import sys
import argparse
import codecs
import logging
import json
from logging import info, warning, debug
from os.path import basename, isfile, isdir, join
from subprocess import check_call

class WebViewUpdater(object):
    all_enviroments = ['dev', 'qa', 'release']
    sync_options = ['--exclude', '*.DS_Store', '--exclude', '*.git', '--delete']
    def __init__(self, root_dir, build_dir, env='all'):
        self.root_dir = root_dir
        self.build_dir = build_dir
        self.envs = [env]
        if self.envs == ['all']:
            self.envs = self.all_enviroments
        self.webview_dir = join(self.root_dir, 'webview')
        self.s3_webview_dir = join('s3://gree-kms-assets', 'webview')

    def generate_json(self, platform):
        for env in self.envs:
            src_path = join(self.root_dir, "webview", env, platform)
            dst_path = join(self.build_dir, "webview", env, platform)
            if not isdir(src_path):
                info("%s does not exists." % src_path)
                continue
            html_files = self.list_html_files(src_path, "kms://")
            if not isdir(dst_path):
                os.makedirs(dst_path)
            dst_file = join(dst_path, "webviews.json")
            info("Generating webview json list for platform %s: %s", platform, dst_file)
            with open(dst_file, 'w') as fout:
                json.dump(html_files, fout, indent=2)
            os.chmod(dst_file, 0664)

    def sync_with_root(self):
        rsync = ['rsync', '-ac', '--exclude', '*.DS_Store']
        for env in self.envs:
            src_path = join(self.build_dir, "webview", env, '')
            dst_path = join(self.root_dir, "webview", env, '')
            cmdline = rsync + [src_path, dst_path]
            debug(' '.join(cmdline))
            check_call(cmdline)


    def list_html_files(self, path, url_prefix):
        if isfile(path) and path.endswith(".html") and basename(path) != "index.html":
            return [os.path.join(url_prefix, basename(path))]
        elif isdir(path):
            children = []
            for item in os.listdir(path):
                children += self.list_html_files(join(path, item), join(url_prefix, basename(path)))
            return children
        return []

    def deploy_dev_cdn(self, dst_root):
        success = True
        for env in self.envs:
            try:
                src = join(self.webview_dir, env, '')
                dst = join(dst_root, env, '')
                self.sync(['rsync', '-ac'], self.sync_options, src, dst)
            except:
                warning("Sync webview/%s to dev cdn failed.", env)
                success = False
        return success

    def deploy_s3_cdn(self):
        success = True
        for env in self.envs:
            try:
                src = join(self.webview_dir, env, '')
                dst = join(self.s3_webview_dir, env, '')
                self.sync(['aws', 's3', 'sync'], self.sync_options, src, dst)
            except:
                warning("Sync webview/%s to s3 cdn failed.", env)
                success = False
        return success

    def sync(self, cmd, options, src, dst):
        cmdline = cmd + options + [src, dst]
        info("Sync: %s", ' '.join(cmdline))
        check_call(cmdline)

if __name__ == "__main__":
    sys.stdout = codecs.lookup('utf_8')[-1](sys.stdout)
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawTextHelpFormatter,
        description = 'update webview assets',
        epilog = """\
commands:
  update          generate webview.json containing containing a list of all the html pages available
  deploy          deploy the dev, qa, release folder under webview to dev cdn & s3 cdn
  update_deploy   update then deploy
examples:
  update webview.json for all environments
      $ ./script/update_webviews.py --root-dir ${ROOT_DIR} update

  deploy webviews to cdn for dev
      $ ./script/update_webviews.py --root-dir ${ROOT_DIR} --environment dev deploy

  update then deploy for all environments
      $ ./script/update_webviews.py --root-dir ${ROOT_DIR} update_deploy
        """)
    parser.add_argument('command',          help = 'command (update|deploy|update_deploy)')
    parser.add_argument('--environment',    help = 'environment (all|dev|qa|release). default: all', default='all')
    parser.add_argument('--root-dir',       help = 'root directory (webview folder\'s parent)', required=True)
    parser.add_argument('--build-dir',      help = 'build directory', required=True)
    parser.add_argument('--cdn-dir',        help = 'cdn directory to deploy. default: /var/www/cdn', default='/var/www/cdn')
    parser.add_argument('--skip-sync-root', help = 'skip syncing build_dir contents to root_dir(ignored if command is `deploy`) (0|1)', default=0, type=int)
    parser.add_argument('--log-level',      help = 'log level (WARNING|INFO|DEBUG). default: INFO', default='INFO')

    args = parser.parse_args()
    logging.basicConfig(level=args.log_level, format='%(asctime)-15s %(levelname)s %(message)s')
    updater = WebViewUpdater(args.root_dir, args.build_dir, args.environment)
    if args.command in ('update', 'update_deploy'):
        updater.generate_json('ios')
        updater.generate_json('android')
        if not args.skip_sync_root:
            updater.sync_with_root()
    if args.command in ('deploy', 'update_deploy'):
        success = updater.deploy_dev_cdn(args.cdn_dir)
        success = updater.deploy_s3_cdn() and success
        if not success:
            exit(1)
    exit(0)

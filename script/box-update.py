#! /usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals
import os
import sys
import shutil
import hashlib
import argparse
import re
import tempfile
import json
import urllib3
import logging

from pprint import pprint
from boxsdk import Client
from boxsdk.exception import BoxAPIException
from boxsdk.object.collaboration import CollaborationRole
from boxsdk import OAuth2

CLIENT_ID = 'mej6etbo3brd22qorp2jcx6dp4q8cy0r'
CLIENT_SECRET = 'cqXZJRcjgbxE7FoZYlpqvwlxyxtZcmNz'

def store_tokens(access_token, refresh_token):
    a = {"access_token":access_token, "refresh_token":refresh_token}
    with open(get_token_file(), "w") as f:
       json.dump(a, f);

def get_base_folders(box_client):
    folders = {}
    f = box_client.folder(folder_id='0').get()
    for item in f["item_collection"]["entries"]:
        folders[item["name"]] = item["id"]
    return folders

def get_token_file():
    return tempfile.gettempdir() + '/admin-token-only.box';


def donwload_dirty_files(box_client, local_path_base="tmp", box_id="0", box_path = "", force_traverse = True):
    folder = box_client.folder(box_id).get(["name","id", "type", "sha1", "item_collection", "modified_at"])
    local_path = local_path_base + "/" + box_path
    meta_path = local_path + ".meta"

    is_dirty = True
    if os.path.exists(meta_path):
        with open(meta_path) as f:
           is_dirty = folder["modified_at"] != f.read()
    if not (is_dirty or force_traverse):
        return

    print("\n" + box_path + ":")

    if not os.path.exists(local_path):
        os.makedirs(local_path)

    local_items = []
    for i in os.listdir(local_path):
        if not (i.endswith(".meta") or i.startswith(".")):
            local_items.append(i)

    for item in folder["item_collection"]["entries"]:
        item_name = item["name"]
        item_id = item["id"]
        item_type = item["type"]

        if item_name in local_items:
            local_items.remove(item_name)

        local_item_path = local_path + "/" + item_name

        if item_type == "folder":
            donwload_dirty_files(box_client=box_client,
                local_path_base=local_path_base,
                box_id=item_id,
                box_path=box_path + "/" + item_name,
                force_traverse=force_traverse)
        elif item_type == "file":
            is_dirty_file = True
            if os.path.exists(local_item_path):
                with open(local_item_path) as f:
                    local_sha1 = hashlib.sha1(f.read()).hexdigest()
                    is_dirty_file = item["sha1"] != local_sha1
            if is_dirty_file:
                print("downloading:" + item_name, end="")
                sys.stdout.flush()
                content = box_client.file(item_id).content()
                d = os.path.dirname(local_item_path)
                with open(local_item_path, "wb") as f:
                    f.write(content)
                print("\tdone")
    for i in local_items:
        i = local_path + "/" + i
        if os.path.isdir(i):
            shutil.rmtree(i)
        else:
            os.remove(i)
        i += ".meta"
        if os.path.exists(i):
            os.remove(i) 
    if is_dirty:
        with open(meta_path, "w") as f:
           f.write(folder["modified_at"])



if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='sync box kms directories', epilog="""\
example:
    $ ./box-update.py path/to/local/box/sync-storage""")
    parser.add_argument('--force_traverse', help='ignore local folder\'s modified-at')
    parser.add_argument('basedir', help='folder where your box folders are synced.')
    args = parser.parse_args()

    with open(get_token_file()) as f:
        j = json.load(f)
        access_token = j["access_token"]
        refresh_token = j["refresh_token"]

    logging.captureWarnings(True)
    base_dir = args.basedir
    force_traverse = args.force_traverse
    oauth = OAuth2(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        access_token=access_token,
        refresh_token=refresh_token,
        store_tokens=store_tokens,
    )
    box_client = Client(oauth)

    if not os.path.exists(base_dir):
        os.makedirs(base_dir)
    for item_name, box_id in get_base_folders(box_client).items():
        if re.match("^kms_[^_]+_asset(_converted)*$", item_name):
            donwload_dirty_files(box_client,
                box_id=box_id,
                local_path_base=base_dir,
                box_path=item_name, 
                force_traverse=force_traverse)
    
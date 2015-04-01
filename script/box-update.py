#! /usr/bin/python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals
import os
import sys
import shutil
import hashlib
import argparse
import re

from pprint import pprint
from boxsdk import Client
from boxsdk.exception import BoxAPIException
from boxsdk.object.collaboration import CollaborationRole
from boxsdk import OAuth2

CLIENT_ID = 'tmfiqodo0t15ln6tns6nuw1m6so4izre'
CLIENT_SECRET = 'ATGmDrTo1qly4Os4HJQF9zNs95qlrK0C'

class store_tokens:
    def __init__(self, access_token, refresh_token):
        #print('token file should be updated')
        print('ACCESS_TOKEN:' + access_token)
        print('REFRESH_TOKEN:' + refresh_token)

def get_base_folders(box_client):
    folders = {}
    f = box_client.folder(folder_id='0').get()
    for item in f["item_collection"]["entries"]:
        folders[item["name"]] = item["id"]
    return folders

def donwload_dirty_files(box_client, local_path_base="tmp", box_id="0", box_path = "", force_traverse = True):
    folder = box_client.folder(box_id).get(["name","id", "type", "sha1", "item_collection", "modified_at"])
    local_path = local_path_base + "/" + box_path
    meta_path = local_path + ".meta"

    is_dirty = True
    if os.path.exists(meta_path):
        with open(meta_path) as f:
           is_dirty = folder["modified_at"] != f.read()
    if not (is_dirty or force_traverse):
        print("skipped " + local_path)
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
            else:
                print("skipped " + local_item_path)
    for i in local_items:
        i = local_path + i
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
    $ ./box-update.py --token_file /tmp/box.json --base_dir /tmp""")

    parser.add_argument('--token_file', required=True, help='token json file path')
    parser.add_argument('--base_dir', required=True, help='local directory to fetch box files')
    parser.add_argument('--force_traverse', help='ignore local folder\'s modified-at')
    args = parser.parse_args()

    with open(args["token_file"]) as f:
        j = json.load(f)
        access_token = j["access_token"]
        refresh_token = j["refresh_token"]

    base_dir = args["base_dir"]
    force_traverse = args["force_traverse"]
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
    
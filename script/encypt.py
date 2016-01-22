#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
import re
import codecs
import json
import argparse
import logging
from logging import info, error, warning
from zlib import compress, decompress
from struct import pack;
from Crypto.Cipher import AES

sys.stdout = codecs.lookup(u'utf_8')[-1](sys.stdout)

def _pad(s):
    bs = AES.block_size
    return s + (bs - len(s) % bs) * chr(bs - len(s) % bs)

def _unpad(s):
    bs = AES.block_size
    pad = ord(s[len(s)-1:])
    if pad < bs:
        return s[:-pad]
    else:
        return s

def encrypt_dir(src_dir, dest_dir, src_ext, dest_ext, aes_key, aes_iv, gzip):
    for root, dirs, files in os.walk(os.path.dirname(src_dir)):
        for file in files:
            name, ext = os.path.splitext(file)
            if not ext[1:] in (src_ext):
                continue

            src_size = 0
            src_file = os.path.join(root, file)
            subdir   = os.path.dirname(re.sub('^'+src_dir, '', src_file))
            with open(src_file, 'r') as f:
                content = org = f.read()
                src_size = len(content)

            if gzip:
                content = compress(content)
            aes = AES.new(aes_key, AES.MODE_CBC, aes_iv)
            enc = aes.encrypt(_pad(content))

            info("%s: %d -> %d" % (os.path.join(subdir, file), src_size, len(enc)))
            '''
            aes = AES.new(aes_key, AES.MODE_CBC, aes_iv)
            dec = decompress(aes.decrypt(enc))
            if dec != org:
                warning("failed to decrypt")
            '''

            dest_file = os.path.join(dest_dir, subdir, name+'.'+dest_ext)
            if not os.path.exists(os.path.dirname(dest_file)):
                os.makedirs(os.path.dirname(dest_file))
            with open(dest_file, 'w') as f:
                f.write(enc)

    return True

if __name__ == '__main__':
    logging.basicConfig(level = logging.INFO, format = '%(asctime)-15s %(levelname)s %(message)s')

    parser = argparse.ArgumentParser(description = 'encrypt files by AES-256-CBC and gzip')
    parser.add_argument('input_dir',  metavar = 'input.dir',  help = 'input dir containing input files')
    parser.add_argument('output_dir', metavar = 'output.dir', help = 'output dir for encrypted files')
    parser.add_argument('aes_key',  help = 'aes 256 key string (32bytes string or file path)')
    parser.add_argument('aes_iv',  help = 'aes iv string (16bytes string or file path)')
    parser.add_argument('--gzip', default = False, action = 'store_true', help = 'compress by zlib before encryption')
    parser.add_argument('--extension', required=True, help = 'input file extension to encrypt in input.dir')
    parser.add_argument('--output-extension', default = 'enc', help = 'output file extension encrpted into output.dir')
    parser.add_argument('--log-level', help = 'log level (WARNING|INFO|DEBUG). default: INFO')
    args = parser.parse_args()
    logging.basicConfig(level = args.log_level or "INFO", format = '%(asctime)-15s %(levelname)s %(message)s')

    info("input dir = %s" % args.input_dir)
    info("output dir = %s" % args.output_dir)
    info("input extension = %s" % args.extension)
    info("output exntension = %s" % args.output_extension)
    info("AES key = %s" % args.aes_key)
    info("AES initial vector = %s" % args.aes_iv)
    info("gzip = %s" % args.gzip)

    aes_values = []
    for aes_value in (args.aes_key, args.aes_iv):
        if not os.path.exists(aes_value):
            aes_values.append(aes_value)
        else:
            with open(aes_value, 'r') as f:
                aes_values.append(f.read().strip())

    encrypt_dir(args.input_dir, args.output_dir, args.extension, args.output_extension, aes_values[0], aes_values[1], args.gzip)

    exit(0)

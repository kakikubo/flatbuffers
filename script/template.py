#!/usr/bin/env python
# -*- coding:utf-8 -*-
 
import os
import json
import argparse
import jinja2

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description = 'generate content from jinja2 template and variable json')
    parser.add_argument('input_template', metavar = 'template.jnj',  help = 'input jinja2 template')
    parser.add_argument('input_json',     metavar = 'variable.json', help = 'input variable json file or string')
    args = parser.parse_args()

    variable = {}
    if os.path.exists(args.input_json):
        with open(args.input_json, 'r') as f:
            variable = json.loads(f.read())
    else:
        variable = json.loads(args.input_json)

    with open(args.input_template, 'r') as f:
        template = jinja2.Template(f.read())
        content = template.render(**variable)
        print(content)
    exit (0)

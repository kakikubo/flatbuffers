#! /usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function
import os
import sys
import re
import argparse
import logging
import json

from logging import info, warning, error
from collections import OrderedDict

def fbs2class(input_fbs, output_header, output_body, output_schema, namespace, with_json, with_msgpack, with_fbs):
    with open(input_fbs, 'r') as f:
        global state, fbs_data
        state = "default"
        fbs_data = OrderedDict({})
        for line in f:
            if state == "default":
                parse_default(line)
            elif state == "table":
                parse_table(line)

    # write user_data.(h|cpp)
    header, body = generate_classes(namespace, with_json, with_msgpack, with_fbs)
    with open(output_header, 'w') as f:
        f.write(header)
    with open(output_body, 'w') as f:
        f.write('#include "'+ os.path.basename(output_header) + '"\n')
        f.write(body)

    # write user_schema.json
    json = generate_schema()
    with open(output_schema, 'w') as f:
        f.write(json)

def parse_default(line):
    global state
    global fbs_data
    global fbs_root_type
    global fbs_namespace
    line = re.sub('\/\/.*', '', line)   # cut comment
    m = re.search('namespace\s+([^;]+);', line)
    if m != None:
        fbs_namespace = m.group(1)
        return
    m = re.search('root_type ([^;]+);', line)
    if m != None:
        fbs_root_type = m.group(1)
        return
    m = re.search('table\s+(\S+)\s+{', line)
    if m == None:
        return
    fbs_data[m.group(1)] = OrderedDict({})
    state = "table"

def parse_table(line):
    global state
    global fbs_data

    name = None
    type = None
    default_value = None
    is_vector = None
    is_hash_key = None
    is_range_key = None
    attribute = None

    # preprocess in comment
    is_hash_key  = re.search('<hash.key>', line)
    is_range_key = re.search('<range.key>', line)
    line = re.sub('\/\/.*', '', line)   # cut comment

    # main parse
    m = re.search('\s*\}', line)
    if m != None:
        state = "default"
        return

    # parse row definition pattern:
    #   columnName:typeName = defaultValue (attr1,attr2,...);
    # defaultValue and attributes are optional.
    m = re.search('\s*(\w+)\s*:\s*(\[?\w+\]?)\s*(=\s*[^(]+)?\s*(\(.+\))?\s*;', line.strip())
    if m:
        name = m.group(1)
        type = re.sub('[\[\]]', '', m.group(2))
        is_vector = re.match('\[(\w+)\]', m.group(2)) is not None
        default_value = re.sub('=\s*', '', re.sub('"', '', m.group(3))) if m.group(3) is not None else None

        # attributes
        attr_string = re.sub('[\(\)]', '', m.group(4)) if m.group(4) is not None else None
        if attr_string is not None:
            attribute = OrderedDict()
            for element in re.split(',\s*', attr_string):
                m = re.search('([^:]+)\s*(:\s*.+)?', element)
                kk = m.group(1)
                if m.lastindex == 2:
                    vv = re.sub('"', '', m.group(2)[1:])
                    attribute[kk] = vv
                elif m.lastindex == 1:
                    attribute[kk] = True
                    if 'hash_key' in attribute.keys():
                        is_hash_key = True
                    if 'key' in attribute.keys():
                        is_range_key = True

    item = OrderedDict()
    item['name'] = name
    item['type'] = item['item_type'] = type
    item['default_value'] = default_value
    item['is_vector'] = is_vector
    item['is_hash_key'] = is_hash_key
    item['is_range_key'] = is_range_key
    item['attribute'] = attribute

    table_name = next(reversed(fbs_data))
    fbs_data[table_name][name] = item

def snake_case(src):
    dest = ''
    prev = None
    for c in src:
        if c.lower() == c:
            dest += c
        elif len(dest) > 0 and prev and prev.upper() != prev:
            dest += '_' + c.lower()
        else:
            dest += c.lower()
        prev = c
    return dest

def upper_camel_case(src):
    return src[0:1].upper() + src[1:]

def get_item_range_key(item, fbs_data, table_property):
    if not item["is_default_type"] and "range_key" in table_property[item["item_type"]]:
        return fbs_data[item["item_type"]][table_property[item["item_type"]]["range_key"]]
    else:
        return None

def generate_classes(namespace=None, with_json=True, with_msgpack=True, with_fbs=False):
    global fbs_data
    global fbs_root_type
    global fbs_namespace

    # initialize cpp header
    h = ''
    h += '#include <jansson.h>\n'
    if with_msgpack:
        h += '#include <msgpack.hpp>\n'
    if with_fbs:
        h += '#include "user_data_generated.h"\n'
    h += '#include "SecureMemory.h"\n'
    h += "\n"

    h += '#pragma clang diagnostic ignored "-Wc++11-extensions"\n'
    h += '#pragma clang diagnostic ignored "-Wunused-variable"\n'
    h += "\n"

    # initialize cpp body
    s = ''
    s += '#include <iomanip>\n'
    s += '#include <sstream>\n'
    s += '#include <openssl/md5.h>\n'
    s += "\n"

    namespace = namespace or fbs_namespace
    for ns in namespace.split('.'):
        h += "namespace " + ns + " {\n"
        s += "namespace " + ns + " {\n"

    h += "\n// class prototypes\n"
    for table_name in fbs_data:
        h += "class " + table_name + ";\n"

    # pre-process
    table_property = {}
    for table_name in fbs_data:
        table = fbs_data[table_name]
        table_property[table_name] = {}
        for item_name, item in table.iteritems():
            if item["is_vector"]:
                table_property[table_name]["has_vector"] = True
            if item["is_hash_key"]:
                table_property[table_name]["hash_key"] = item_name
            if item["is_range_key"]:
                table_property[table_name]["range_key"] = item_name

            item["is_default_type"] = not item["item_type"] in fbs_data
            item["is_secure"] = False
            if item["item_type"] == "string":
                item["cpp_type"] = item["cpp_secure_type"] = "std::string"
            elif item["item_type"] == "long":
                item["cpp_type"] = "long long"
                item["cpp_secure_type"] = "WFS::SecureMemory<long long>"
                item["is_secure"] = True
            elif item["is_default_type"]:
                item["cpp_type"] = item["item_type"]
                item["cpp_secure_type"] = "WFS::SecureMemory<" + item["item_type"]  + ">"
                item["is_secure"] = True
            else:
                item["cpp_type"] = item["cpp_secure_type"] = "std::shared_ptr<" + item["item_type"] + ">"

    # static functions
    # calcChecksum
    h += "\n// calcurate MD5 checksum\n"
    h += "std::string calcChecksum(const unsigned char* data, size_t len);\n"
    s += "\nstd::string calcChecksum(const unsigned char* data, size_t len) {\n"
    s += "  unsigned char buf[MD5_DIGEST_LENGTH];\n"
    s += "  MD5(data, len, buf);\n"
    s += "  std::stringstream hex;\n"
    s += "  hex << std::hex << std::nouppercase << std::setfill('0');\n"
    s += "  for (int i = 0; i < MD5_DIGEST_LENGTH; i++) {\n"
    s += "    hex << std::setw(2) << (unsigned short)buf[i];\n"
    s += "  }\n"
    s += "  return hex.str();\n"
    s += "}\n"

    # main generating
    h += "\n// main class definitions\n"
    for table_name in fbs_data:
        table = fbs_data[table_name]
        prop  = table_property[table_name]

        h += "class " + table_name + " {\n protected:\n"
        for item_name, item in table.iteritems():
            if item["is_vector"]:
                h += "  // " + item_name + "\n"
                h += "  std::vector<" + item["cpp_secure_type"] + " > _" + item_name + ";\n"
                h += "  std::vector<" + item["cpp_type"] + " > _" + item_name + "Erased;\n"
                range_key = get_item_range_key(item, fbs_data, table_property)
                if range_key:
                    h += "  std::map<" + range_key["cpp_type"] + ", " + item["cpp_secure_type"] + " > _" + item_name + "Map;\n"
            else:
                h += "  " + item["cpp_secure_type"] + " _" + item_name + "; // " + item_name + "\n"
        h += "\n"
        h += "  time_t __timestamp;\n"
        h += "  bool __dirty;\n"

        h += "\n public:\n"
        # constructor
        h += "  // constructor\n"
        h += "  " + table_name + "();\n"
        inits = []
        for item_name, item in table.iteritems():
            item_type = item["item_type"]
            default_value = ""
            if item["attribute"] and item["attribute"].has_key("default"):
                value = item["attribute"].has_key("default")
                if item_type in ('string'):
                    default_value = '"'+value+'"';
                elif item_type in ('bool'):
                    default_value = "true" if value else  "false";
                else:
                    default_value = value;

            if not item["is_default_type"] and not item["is_vector"]:
                inits.append("  _" + item_name + "(std::make_shared<" + item["item_type"] + " >("+default_value+")),\n")
            elif default_value:
                inits.append("  _" + item_name + "(" + default_value + "),\n")
        s += "\n\n\n"
        s += "// " + table_name + "\n"
        s += "" + table_name + "::" + table_name + "() : \n" + "".join(inits) + "  __timestamp(-1),\n  __dirty(true) {}\n"

        # getter
        h += "\n  // getters\n"
        for item_name, item in table.iteritems():
            if item["is_vector"]:
                h += "  const std::vector<" + item["cpp_secure_type"] + " >* " + item_name + "() const { return &_" + item_name + "; }\n"
                range_key = get_item_range_key(item, fbs_data, table_property)
                if range_key:
                    h += "  " + item["cpp_type"] + " lookup" + upper_camel_case(item_name) + "(" + range_key["cpp_type"] + " needle);\n"
                    s += "\n" + item["cpp_type"] + " " + table_name + "::lookup" + upper_camel_case(item_name) + "(" + range_key["cpp_type"] + " needle) {\n"
                    s += "  auto found = _" + item_name + "Map.find(needle);\n"
                    s += "  if (found == _" + item_name + "Map.end()) {\n"
                    s += "    return nullptr;\n"
                    s += "  }\n"
                    if item["is_secure"]:
                        s += "  return found->second.getValue();\n"
                    else:
                        s += "  return found->second;\n"
                    s += "}\n"
            elif item["is_secure"]:
                h += "  " + item["cpp_type"] + " " + item_name + "() const { return _" + item_name + ".getValue(); }\n"
            else:
                h += "  " + item["cpp_type"] + " " + item_name + "() const { return _" + item_name + "; }\n"

        # setter
        h += "\n  // setters\n"
        for item_name, item in table.iteritems():
            if item["is_vector"]:
                # set
                range_key = get_item_range_key(item, fbs_data, table_property)
                if range_key:
                    h += "  void set" + upper_camel_case(item_name) + "(int pos, const " + item["cpp_type"] + "& value);\n"
                    s += "\nvoid " + table_name + "::set" + upper_camel_case(item_name) + "(int pos, const " + item["cpp_type"] + "& value) {\n"
                    s += "  if (_" + item_name + "[pos]) _" + item_name + "Map.erase(_" + item_name + "[pos]->" + range_key["name"] + "());\n"
                    s += "  " + item["cpp_secure_type"] + " __value(value);\n"
                    s += "  _" + item_name + "Map[value->" + range_key["name"] + "()] = __value;\n"
                    s += "  _" + item_name + "[pos] = __value;\n"
                    s += "  __dirty = true;\n"
                    s += "}\n"
                else:
                    h += "  void set" + upper_camel_case(item_name) + "(int pos, const " + item["cpp_type"] + "& value, const " + item["cpp_type"] + "& defaultValue);\n"
                    s += "\nvoid " + table_name + "::set" + upper_camel_case(item_name) + "(int pos, const " + item["cpp_type"] + "& value, const " + item["cpp_type"] + "& defaultValue) {\n"
                    s += "  if (_" + item_name + ".size() <= pos) {\n"
                    s += "    " + item["cpp_secure_type"] + " __value = defaultValue;\n"
                    s += "    _" + item_name + ".resize(pos + 1, __value);\n"
                    s += "  }\n"
                    s += "  " + item["cpp_secure_type"] + " __value(value);\n"
                    s += "  _" + item_name + "[pos] = __value;\n"
                    s += "  __dirty = true;\n"
                    s += "}\n"

                # emplace
                if item["item_type"] != "bool":
                    h += "  void emplace" + upper_camel_case(item_name) + "(std::vector<" + item["cpp_secure_type"] + " >::const_iterator pos, const " + item["cpp_type"] + "& value);\n"
                    s += "\nvoid " + table_name + "::emplace" + upper_camel_case(item_name) + "(std::vector<" + item["cpp_secure_type"] + " >::const_iterator pos, const " + item["cpp_type"] + "& value) {\n"
                    s += "  " + item["cpp_secure_type"] + " __value(value);\n"
                    s += "  _" + item_name + ".emplace(pos, __value);\n"
                    if range_key:
                        s += '  assert(_' + item_name + 'Map.find(value->' + range_key["name"] + '()) == _' + item_name + 'Map.end());\n'
                        s += "  _" + item_name + "Map[value->" + range_key["name"] + "()] = __value;\n"
                    s += "  __dirty = true;\n"
                    s += "}\n"

                # insert
                h += "  void insert" + upper_camel_case(item_name) + "(std::vector<" + item["cpp_secure_type"] + " >::const_iterator pos, const " + item["cpp_type"] + "& value);\n"
                s += "\nvoid " + table_name + "::insert" + upper_camel_case(item_name) + "(std::vector<" + item["cpp_secure_type"] + " >::const_iterator pos, const " + item["cpp_type"] + "& value) {\n"
                s += "  " + item["cpp_secure_type"] + " __value(value);\n"
                s += "  _" + item_name + ".insert(pos, __value);\n"
                if range_key:
                    s += '  assert(_' + item_name + 'Map.find(value->' + range_key["name"] + '()) == _' + item_name + 'Map.end());\n'
                    s += "  _" + item_name + "Map[value->" + range_key["name"] + "()] = __value;\n"
                s += "  __dirty = true;\n"
                s += "}\n"

                # pushBack
                h += "  void pushBack" + upper_camel_case(item_name) + "(const " + item["cpp_type"] + "& value);\n"
                s += "\nvoid " + table_name + "::pushBack" + upper_camel_case(item_name) + "(const " + item["cpp_type"] + "& value) {\n"
                s += "  " + item["cpp_secure_type"] + " __value(value);\n"
                s += "  _" + item_name + ".push_back(__value);\n"
                if range_key:
                    s += '  assert(_' + item_name + 'Map.find(value->' + range_key["name"] + '()) == _' + item_name + 'Map.end());\n'
                    s += "  _" + item_name + "Map[value->" + range_key["name"] + "()] = __value;\n"
                s += "  __dirty = true;\n"
                s += "}\n"

                # erase
                h += "  void erase" + upper_camel_case(item_name) + "(std::vector<" + item["cpp_secure_type"] + " >::const_iterator pos);\n"
                s += "\nvoid " + table_name + "::erase" + upper_camel_case(item_name) + "(std::vector<" + item["cpp_secure_type"] + " >::const_iterator pos) {\n"
                if range_key:
                    s += "  _" + item_name + "Map.erase((*pos)->" + range_key["name"] + "());\n"
                s += "  _" + item_name + "Erased.push_back(*pos);\n"
                s += "  _" + item_name + ".erase(pos);\n"
                s += "  // __dirty = true; // erase is not dirty\n"
                s += "}\n"

                # clear
                h += "  void clear" + upper_camel_case(item_name) + "();\n"
                s += "\nvoid " + table_name + "::clear" + upper_camel_case(item_name) + "() {\n"
                s += "  for (auto __v : _" + item_name + ") {\n"
                s += "    _" + item_name + "Erased.push_back(__v);\n"
                s += "  }\n"
                s += "  _" + item_name + ".clear();\n"
                if range_key:
                    s += "  _" + item_name + "Map.clear();\n"
                s += "  // __dirty = true; // erase is not dirty\n"
                s += "}\n"
            elif item["is_default_type"]:
                # set 
                h += "  void set" + upper_camel_case(item_name) + "(" + item["cpp_type"] + " value);\n"
                s += "\nvoid " + table_name + "::set" + upper_camel_case(item_name) + "(" + item["cpp_type"] + " value) { \n"
                s += "  " + item["cpp_secure_type"] + " __value(value);\n"
                s += "  _" + item_name + " = __value;\n"
                s += "  __dirty = true;\n"
                s += "}\n"
                if item["item_type"] == 'string':
                    h += "  void set" + upper_camel_case(item_name) + "(const char* value);\n"
                    s += "void " + table_name + "::set" + upper_camel_case(item_name) + "(const char* value) {\n"
                    s += "  " + item["cpp_secure_type"] + " __value(value);\n"
                    s += "  _" + item_name + " = __value;\n"
                    s += "  __dirty = true;\n"
                    s += "}\n"

        h += "\n  // dirty flag\n"
        # idDirty
        h += "  bool isDirty() const { return __dirty; }\n"
        h += "  bool isDirtyRecursive();\n"
        s += "\nbool " + table_name + "::isDirtyRecursive() {\n"
        s += "  if (__dirty) return true;\n"
        for item_name, item in table.iteritems():
            if not item["is_default_type"] and item["is_vector"]:
                s += "  for (auto it = _" + item_name + ".begin(); it != _" + item_name + ".end(); it++) {\n"
                s += "    if ((*it)->isDirtyRecursive()) {\n"
                s += "      __dirty = true;  // bump up to parent\n"
                s += "      return true;\n"
                s += "    }\n"
                s += "  }\n"
            elif not item["is_default_type"]:
                s += "  if (_" + item_name + "->isDirtyRecursive()) {\n"
                s += "    __dirty = true;  // bump up to parent\n"
                s += "    return true;\n"
                s += "  }\n"
        s += "  return false;\n"
        s += "}\n"

        # clearDirty
        h += "  void clearDirty() { __dirty = false; }\n"
        h += "  void clearDirtyRecursive();\n"
        s += "\nvoid " + table_name + "::clearDirtyRecursive() {\n"
        for item_name, item in table.iteritems():
            if not item["is_default_type"] and item["is_vector"]:
                s += "  for (auto it = _" + item_name + ".begin(); it != _" + item_name + ".end(); it++) {\n"
                s += "    (*it)->clearDirtyRecursive();\n"
                s += "  }\n"
            elif not item["is_default_type"]:
                s += "  _" + item_name + "->clearDirtyRecursive();\n"
        s += "  __dirty = false;\n"
        s += "}\n"

        h += "\n  // general accessor\n"
        if fbs_root_type == table_name:
            # keys
            h += "  std::vector<std::string> keys();\n"
            s += "\nstd::vector<std::string> " + table_name + "::keys() {\n"
            s += "  std::vector<std::string> _keys;\n"
            for item_name in table:
                s += '  _keys.push_back("' + item_name + '");\n'
            s += "  return _keys;\n"
            s += "}\n"

            # tables
            h += "  std::vector<std::string> tables();\n"
            s += "\nstd::vector<std::string> " + table_name + "::tables() {\n"
            s += "  std::vector<std::string> _tables;\n"
            for item_name, item in table.iteritems():
                s += '  _tables.push_back("' + item["item_type"] + '");\n'
            s += "  return _tables;\n"
            s += "}\n"

            # getTableName
            h += "  const char* getTableName(const std::string& target);\n"
            s += "\nconst char* " + table_name + "::getTableName(const std::string& target) {\n"
            for item_name, item in table.iteritems():
                s += '  if (target == "' + item_name + '") return "' + item["item_type"] + '";\n'
            s += '  return "";\n'
            s += "}\n"

            # getKey
            h += "  const char* getKey(const std::string& target);\n"
            s += "\nconst char* " + table_name + "::getKey(const std::string& target) {\n"
            for item_name, item in table.iteritems():
                s += '  if (target == "' + item["item_type"] + '") return "' + item_name + '";\n'
            s += '  return "";\n'
            s += "}\n"

            # getHashKey
            h += "  const char* getHashKey(const std::string& target);\n"
            s += "\nconst char* " + table_name + "::getHashKey(const std::string& target) {\n"
            for item_name, item in table.iteritems():
                if item["is_vector"]:
                  s += '  if (target == "' + item["item_type"] + '" && _' + item_name + '.size() > 0) return _' + item_name + '.at(0)->hashKey();\n'
                else:
                  s += '  if (target == "' + item["item_type"] + '") return _' + item_name + '->hashKey();\n'
            s += '  return "";\n'
            s += "}\n"

            # getRangeKey
            h += "  const char* getRangeKey(const std::string& target);\n"
            s += "\nconst char* " + table_name + "::getRangeKey(const std::string& target) {\n"
            for item_name, item in table.iteritems():
                if not "range_key" in table_property[item["item_type"]]:
                    continue
                if item["is_vector"]:
                  s += '  if (target == "' + item["item_type"] + '" && _' + item_name + '.size() > 0) return _' + item_name + '.at(0)->rangeKey();\n'
                else:
                  s += '  if (target == "' + item["item_type"] + '") return _' + item_name + '->rangeKey();\n'
            s += '  return "";\n'
            s += "}\n"

            # collectRangeKey
            h += "  std::vector<int> collectRangeKey(const std::string& target);\n"
            s += "\nstd::vector<int> " + table_name + "::collectRangeKey(const std::string& target) {\n"
            s += '  std::vector<int> rangeKeys;\n'
            for item_name, item in table.iteritems():
                if not "range_key" in table_property[item["item_type"]]:
                    continue
                s += '  if (target == "' + item_name + '") {\n'
                if item["is_vector"]:
                    s += "    for (auto it = _" + item_name + ".begin(); it != _" + item_name + ".end(); it++) {\n"
                    s += "      rangeKeys.push_back((*it)->rangeKeyValue());\n"
                    s += "    }\n"
                else:
                    s += '    rangeKeys.push_back(_' + item_name + '->rangeKeyValue());\n'
                s += '    return rangeKeys;\n'
                s += '  }\n'
            s += '  return rangeKeys;\n'
            s += '}\n'

            # collectErasedRangeKey
            h += "  std::vector<int> collectErasedRangeKey(const std::string& target);\n"
            s += "\nstd::vector<int> " + table_name + "::collectErasedRangeKey(const std::string& target) {\n"
            s += '  std::vector<int> rangeKeys;\n'
            for item_name, item in table.iteritems():
                if not "range_key" in table_property[item["item_type"]]:
                    continue
                s += '  if (target == "' + item_name + '") {\n'
                if item["is_vector"]:
                    s += "    for (auto it = _" + item_name + "Erased.begin(); it != _" + item_name + "Erased.end(); it++) {\n"
                    s += "      rangeKeys.push_back((*it)->rangeKeyValue());\n"
                    s += "    }\n"
                s += '    return rangeKeys;\n'
                s += '  }\n'
            s += '  return rangeKeys;\n'
            s += '}\n'

        # hashKey
        if "hash_key" in prop:
            hash_key = prop["hash_key"]
            h += '  const char* hashKey() const { return "' + hash_key + '"; }\n'
            h += "  const " + table[hash_key]["cpp_type"] + " hashKeyValue() const { return _" + hash_key + "; }\n"
            h += "  long setHashKey(long v);\n"
            s += "\nlong " + table_name + "::setHashKey(long v) {\n"
            s += "  if (v != _" + hash_key + ") {\n"
            s += "    _" + hash_key + " = v;\n" 
            s += "    __dirty = true;\n"
            s += "  }\n"
            s += "  return v;\n"
            s += "}\n"

        # rangeKey
        if "range_key" in prop:
            range_key = prop["range_key"]
            h += '  const char* rangeKey() const { return "' + range_key + '"; }\n'
            h += "  const " + table[range_key]["cpp_type"] + " rangeKeyValue() const { return _" + range_key + "; }\n"
            h += "  int setRangeKey(int v);\n"
            s += "\nint " + table_name + "::setRangeKey(int v) {\n"
            s += "  if (!_" + range_key + ") {\n"
            s += "    _" + range_key + " = v++;\n" 
            s += "    __dirty = true;\n"
            s += "  }\n"
            s += "  return v;\n"
            s += "}\n"

        # completeKey
        h += "  int completeKey(long hashKey, int rangeKey);\n"
        s += "\nint " + table_name + "::completeKey(long hashKey, int rangeKey) {\n"
        for item_name, item in table.iteritems():
            if item["is_hash_key"]:
                s += "  setHashKey(hashKey);\n"
            elif item["is_range_key"]:
                s += "  rangeKey = setRangeKey(rangeKey);\n"
            elif not item["is_default_type"]:
                if item["is_vector"]:
                    s += "  for (auto it = _" + item_name + ".begin(); it != _" + item_name + ".end(); it++) {\n"
                    s += "    rangeKey = (*it)->completeKey(hashKey, rangeKey);\n"
                    s += "  }\n"
                else:
                    s += "  rangeKey = _" + item_name + "->completeKey(hashKey, rangeKey);\n"
        s += "  return rangeKey;\n"
        s += "}\n"

        # completeHashKey
        h += "  void completeHashKey(long hashKey);\n"
        s += "\nvoid " + table_name + "::completeHashKey(long hashKey) {\n"
        for item_name, item in table.iteritems():
            if item["is_hash_key"]:
                s += "  setHashKey(hashKey);\n"
            elif not item["is_default_type"]:
                if item["is_vector"]:
                    s += "  for (auto it = _" + item_name + ".begin(); it != _" + item_name + ".end(); it++) {\n"
                    s += "    (*it)->completeHashKey(hashKey);\n"
                    s += "  }\n"
                else:
                    s += "  _" + item_name + "->completeHashKey(hashKey);\n"
        s += "}\n"

        if with_json:
            h += "\n  // json\n"
            # toJson
            h += "  json_t* toJson(bool onlyDirty);\n"
            s += "\njson_t* " + table_name + "::toJson(bool onlyDirty) {\n"
            s += "  if (onlyDirty && !isDirty()) return nullptr;\n"
            s += "  auto json = json_object();\n"
            for item_name, item in table.iteritems():
                item_type = item["item_type"]
                if item["is_vector"]:
                    s += "  auto a_" + item_name + " = json_array();\n"
                    s += "  for (auto it = _" + item_name + ".begin(); it != _" + item_name + ".end(); it++) {\n"
                    if item_type == 'string':
                        s += "    json_array_append_new(a_" + item_name + ", json_string((*it).c_str()));\n"
                    elif item_type in ('int', 'long'):
                        s += "    json_array_append_new(a_" + item_name + ", json_integer(it->getValue()));\n"
                    elif item_type in ('float', 'double'):
                        s += "    json_array_append_new(a_" + item_name + ", json_real(it->getValue()));\n"
                    elif item_type in ('bool'):
                        s += "    json_array_append_new(a_" + item_name + ", json_boolean(it->getValue()));\n"
                    else:
                        s += "    json_array_append_new(a_" + item_name + ", (*it)->toJson(false));\n"
                    s += "  }\n"
                    s += '  json_object_set_new(json, "' + item_name + '", a_' + item_name + ');\n'
                elif item_type == 'string':
                    s += '  json_object_set_new(json, "' + item_name + '", json_string(_' + item_name + '.c_str()));\n'
                elif item_type in ('int', 'long'):
                    s += '  json_object_set_new(json, "' + item_name + '", json_integer(_' + item_name + '.getValue()));\n'
                elif item_type in ('float', 'double'):
                    s += '  json_object_set_new(json, "' + item_name + '", json_real(_' + item_name + '.getValue()));\n'
                elif item_type in ('bool'):
                    s += '  json_object_set_new(json, "' + item_name + '", json_boolean(_' + item_name + '.getValue()));\n'
                else:
                    s += '  json_object_set_new(json, "' + item_name + '", _' + item_name + '->toJson(false));\n'
            s += "  return json;\n";
            s += "}\n"

            # fromJson
            h += "  void fromJson(json_t* json);\n"
            s += "\nvoid " + table_name + "::fromJson(json_t* json) {\n"
            if "has_vector" in prop:
                s += "  int i;\n"
                s += "  json_t* v;\n"
            for item_name, item in table.iteritems():
                item_type = item["item_type"]
                range_key = get_item_range_key(item, fbs_data, table_property)
                s += '  auto __' + item_name + ' = json_object_get(json, "' + item_name + '");\n'
                s += '  if (__' + item_name + ') {\n'
                if item["is_vector"]:
                    s += "    _" + item_name + ".clear();\n"
                    if range_key:
                        s += "    _" + item_name + "Map.clear();\n"
                    s += '    json_array_foreach(__' + item_name + ', i, v) {\n'
                    if item_type in ('string'):
                        s += "      pushBack" + upper_camel_case(item_name) + "(json_string_value(v));\n"
                    elif item_type in ('int'):
                        s += "      pushBack" + upper_camel_case(item_name) + "(static_cast<int>(json_integer_value(v)));\n"
                    elif item_type in ('long'):
                        s += "      pushBack" + upper_camel_case(item_name) + "(static_cast<long>(json_integer_value(v)));\n"
                    elif item_type in ('float', 'double'):
                        s += "      pushBack" + upper_camel_case(item_name) + "(json_real_value(v));\n"
                    elif item_type in ('bool'):
                        s += "      pushBack" + upper_camel_case(item_name) + "(json_boolean_value(v));\n"
                    else:
                        s += "      pushBack" + upper_camel_case(item_name) + "(std::make_shared<" + item["item_type"] + " >(v));\n"
                    s += "    }\n"
                elif item_type in ('string'):
                    s += "    set" + upper_camel_case(item_name) + '(json_string_value(__' + item_name + '));\n'
                elif item_type in ('int'):
                    s += "    set" + upper_camel_case(item_name) + '(static_cast<int>(json_integer_value(__' + item_name + ')));\n'
                elif item_type in ('long'):
                    s += "    set" + upper_camel_case(item_name) + '(static_cast<long>(json_integer_value(__' + item_name + ')));\n'
                elif item_type in ('float', 'double'):
                    s += "    set" + upper_camel_case(item_name) + '(json_real_value(__' + item_name + '));\n'
                elif item_type in ('bool'):
                    s += "    set" + upper_camel_case(item_name) + '(json_boolean_value(__' + item_name + '));\n'
                else:
                    s += "    _" + item_name + '->fromJson(__' + item_name + ');\n'
                s += '  }\n'
            s += "  clearDirty();\n"
            s += "}\n"
            # constructor with json
            h += "  " + table_name + "(json_t* json) { fromJson(json); }\n"

        if with_msgpack:
            h += "\n  // msgpack\n"
            # toMsgpack
            h += "  void toMsgpack(msgpack::packer<msgpack::sbuffer>& pk);\n"
            s += "\nvoid " + table_name + "::toMsgpack(msgpack::packer<msgpack::sbuffer>& pk) {\n"
            s += "  pk.pack_map(%d);\n" % len(table)
            for item_name, item in table.iteritems():
                s += '  pk.pack(std::string("' + item_name + '"));\n'
                if item["is_vector"]:
                    s += '  pk.pack_array((int)_' + item_name + '.size());\n'
                    s += '  for (auto it = _' + item_name + '.begin(); it != _' + item_name + '.end(); it++) {\n'
                    if item["item_type"] == "bool":
                        s += '    pk.pack(it->getValue() ? true : false);\n'
                    elif item["is_secure"]:
                        s += '    pk.pack(it->getValue());\n'
                    elif item["is_default_type"]:
                        s += '    pk.pack(*it);\n'
                    else:
                        s += '    (*it)->toMsgpack(pk);\n'
                    s += '  }\n'
                elif item["item_type"] == "bool":
                    s += '  pk.pack(_' + item_name + '.getValue() ? true : false);\n'
                elif item["is_secure"]:
                    s += '  pk.pack(_' + item_name + '.getValue());\n'
                elif item["is_default_type"]:
                    s += '  pk.pack(_' + item_name + ');\n'
                else:
                    s += '  _' + item_name + '->toMsgpack(pk);\n'
            s += "}\n"

            # fromMsgpack
            h += "  void fromMsgpack(msgpack::object& obj);\n"
            s += "\nvoid " + table_name + "::fromMsgpack(msgpack::object& obj) {\n"
            s += "  std::map<std::string, msgpack::object> __map = obj.as<std::map<std::string, msgpack::object> >();\n"
            for item_name, item in table.iteritems():
                range_key = get_item_range_key(item, fbs_data, table_property)
                s += '  auto __v_' + item_name + ' = __map.find("' + item_name + '");\n'
                s += '  if (__v_' + item_name + ' != __map.end()) {\n'
                if item["is_vector"]:
                    s += "    _" + item_name + ".clear();\n"
                    if range_key:
                        s += "    _" + item_name + "Map.clear();\n"
                    s += '    auto __' + item_name + ' = __v_' + item_name + '->second.as<msgpack::object>();\n';
                    s += '    for (msgpack::object* p(__' + item_name + '.via.array.ptr), * const pend(__' + item_name + '.via.array.ptr + __' + item_name + '.via.array.size); p < pend; ++p) {\n'
                    if item["is_default_type"]:
                        s += '      pushBack' + upper_camel_case(item_name) + '(p->as<' + item["cpp_type"] + '>());\n'
                    else:
                        s += '      pushBack' + upper_camel_case(item_name) + '(std::make_shared<' + item["item_type"] + ' >(*p));\n'
                    s += '    }\n'
                elif item["is_default_type"]:
                    s += '    set' + upper_camel_case(item_name) + '(__v_' + item_name + '->second.as<' + item["cpp_type"] + ' >());\n'
                else:
                    s += '    _' + item_name + '->fromMsgpack(__v_' + item_name + '->second);\n'
                s += '  }\n'
            s += "  clearDirty();\n"
            s += "}\n"
            # constructor with msgpack
            h += "  " + table_name + "(msgpack::object& obj) { fromMsgpack(obj); }\n"

        if with_json and fbs_root_type == table_name:
            # serializeJson
            h += "\n  // top level of JSON IO\n"
            h += "  json_t* serializeJson(const std::string& target, bool onlyDirty);\n"
            s += "\njson_t* " + table_name + "::serializeJson(const std::string& target, bool onlyDirty) {\n"
            for item_name, item in table.iteritems():
                s += '  if (target == "' + item_name + '") {\n'
                if item["is_vector"]:
                    s += '    auto a_' + item_name + ' = json_array();\n'
                    s += '    for (auto it = _' + item_name + '.begin(); it != _' + item_name + '.end(); it++) {\n'
                    s += '      if (onlyDirty && !(*it)->isDirtyRecursive()) continue;\n'
                    s += '      auto __j = (*it)->toJson(onlyDirty);\n'
                    s += '      if (__j != nullptr) json_array_append(a_' + item_name + ', __j);\n'
                    s += '    }\n'
                    s += '    if (!onlyDirty || json_array_size(a_' + item_name +') > 0) {\n'
                    s += '      return a_' + item_name +';\n'
                    s += '    } else {\n'
                    s += '      json_decref(a_' + item_name + ');\n'
                    s += '      return json_null();\n'
                    s += '    }\n'
                else:
                    s += '    if (onlyDirty && !_' + item_name + '->isDirtyRecursive()) return json_null();\n'
                    s += '    return _' + item_name + '->toJson(onlyDirty);\n'
                s += '  }\n'
            s += "  return json_null();\n"
            s += "}\n"

            # deserializeJson
            h += "  void deserializeJson(json_t* json, const std::string& target);\n"
            s += "\nvoid " + table_name + "::deserializeJson(json_t* json, const std::string& target) {\n"
            if "has_vector" in prop:
                s += "  int i;\n"
                s += "  json_t* v;\n"
            for item_name, item in table.iteritems():
                range_key = get_item_range_key(item, fbs_data, table_property)
                s += '  if (target == "' + item_name + '") {\n'
                if item["is_vector"]:
                    s += "    _" + item_name + ".clear();\n"
                    if range_key:
                        s += "    _" + item_name + "Map.clear();\n"
                    s += "    json_array_foreach(json, i, v) {\n"
                    s += "      auto __" + item_name + " = std::make_shared<" + item["item_type"] + ">();\n"
                    s += "      __" + item_name + "->fromJson(v);\n"
                    s += "      pushBack" + upper_camel_case(item_name) + "(__" + item_name + ");\n"
                    s += '    }\n'
                else:
                    s += '    _' + item_name + '->fromJson(json);\n'
                s += '    return;\n'
                s += '  }\n'
            s += "}\n"

        if with_msgpack and fbs_root_type == table_name:
            h += "\n  // top level of msgpack IO\n"
            # serializeMsgpack
            h += "  void serializeMsgpack(msgpack::packer<msgpack::sbuffer>& pk, const std::string& target);\n"
            s += "\nvoid " + table_name + "::serializeMsgpack(msgpack::packer<msgpack::sbuffer>& pk, const std::string& target) {\n"
            for item_name, item in table.iteritems():
                s += '  if (target == "' + item_name + '") {\n'
                if item["is_vector"]:
                    s += '    pk.pack_array((int)_' + item_name + '.size());\n'
                    s += '    for (auto it = _' + item_name + '.begin(); it != _' + item_name + '.end(); it++) {\n'
                    s += '      (*it)->toMsgpack(pk);\n'
                    s += '    }\n'
                else:
                    s += '    _' + item_name + '->toMsgpack(pk);\n'
                s += '    return;\n'
                s += '  }\n'
            s += "}\n"

            # deserializeMsgpack
            h += "  void deserializeMsgpack(msgpack::object& obj, const std::string& target);\n"
            s += "\nvoid " + table_name + "::deserializeMsgpack(msgpack::object& obj, const std::string& target) {\n"
            for item_name, item in table.iteritems():
                range_key = get_item_range_key(item, fbs_data, table_property)
                s += '  if (target == "' + item_name + '") {\n'
                if item["is_vector"]:
                    s += "    _" + item_name + ".clear();\n"
                    if range_key:
                        s += "    _" + item_name + "Map.clear();\n"
                    s += '    for (msgpack::object* p(obj.via.array.ptr), * const pend(obj.via.array.ptr + obj.via.array.size); p < pend; ++p) {\n'
                    s += '      auto __' + item_name + ' = std::make_shared<' + item["item_type"] + '>();\n'
                    s += '      __' + item_name + '->fromMsgpack(*p);\n'
                    s += "      pushBack" + upper_camel_case(item_name) + "(__" + item_name + ");\n"
                    s += '    }\n'
                else:
                    s += '    _' + item_name + '->fromMsgpack(obj);\n'
                s += '    return;\n'
                s += '  }\n'
            s += "}\n"

        if with_fbs:
            # FIXME treat fbs::
            # toFlatbuffers
            h += "\n  // for FlatBuffers\n"
            h += "  flatbuffers::Offset<fbs::" + table_name + "> toFlatbuffers(flatbuffers::FlatBufferBuilder *fbb);\n"
            s += "\nflatbuffers::Offset<fbs::" + table_name + "> " + table_name + "::toFlatbuffers(flatbuffers::FlatBufferBuilder *fbb) {\n"
            for item_name, item in table.iteritems():
                if item["is_vector"]:
                    s += "  // vector of " + item_name + "\n";
                    s += "  std::vector<" + item["cpp_secure_type"] + " __" + item_name + ";\n"
                    s += "  for (auto it = _" + item_name + ".begin(); it != _" + item_name + ".end(); it++) {\n"
                    if item["item_type"] == 'string':
                        s += "    __" + item_name + "->pushBack" + upper_camel_case(item_name) + "(fbb->CreateString(*it));\n"
                    elif item["is_default_type"]:
                        s += "    __" + item_name + "->pushBack" + upper_camel_case(item_name) + "(*it);\n"
                    else:
                        s += "    __" + item_name + "->pushBack" + upper_camel_case(item_name) + "((*it)->toFlatbuffers(fbb));\n"
                    s += "  }\n"
                    s += "  auto fb_" + item_name + " = fbb->CreateVector(__" + item_name + ");\n"
                elif item["item_type"] == 'string':
                    s += "  auto fb_" + item_name + " = fbb->CreateString(_" + item_name + ");\n"
                elif item["is_default_type"]:
                    s += "  auto fb_" + item_name + " = _" + item_name + ";\n"
                else:
                    s += "  auto fb_" + item_name + " = _" + item_name + "->toFlatbuffers(fbb);\n"
            s += "  return fbs::Create" + upper_camel_case(table_name) + "(*fbb,\n"
            remains = len(table)
            for item_name, item in table.iteritems():
                s += "    fb_" + item_name
                remains -= 1
                if remains == 0:
                    s += ");\n"
                else:
                    s += ",\n"
            s += "}\n"

        # checksum
        h += "\n  // calcurate MD5 checksum\n"
        h += "  std::string checksum();\n"
        s += "\nstd::string " + table_name + "::checksum() {\n"
        if with_msgpack:
            s += "  msgpack::sbuffer sbuf;\n"
            s += "  msgpack::packer<msgpack::sbuffer> pk(&sbuf);\n"
            s += "  toMsgpack(pk);\n"
            s += "  return " + "::".join(namespace.split('.')) + "::calcChecksum(reinterpret_cast<const unsigned char*>(sbuf.data()), sbuf.size());\n"
        elif with_json:
            s += "  std::string data = json_dumps(toJson(), JSON_COMPACT | JSON_ENCODE_ANY);\n"
            s += "  return " + "::".join(namespace.split('.')) + "::calcChecksum(reinterpret_cast<const unsigned char*>(data.c_str()), data.length());\n"
        else:
            s += '  std::string data("no available format");\n'
        s += "}\n"

        # end of class
        h += "};\n\n" 

    if with_fbs:
        # serializeFbs
        h += "std::vector<char> serializeFbs();\n"
        s += "\nstd::vector<char> " + table_name + "::serializeFbs() {\n"
        s += "  flatbuffers::FlatBufferBuilder fbb;\n"
        s += "  auto data = " + fbs_root_type + ".toFlatbuffers(&fbb);\n"
        s += "  fbb.Finish(data);\n"
        s += "  return std::vector<char>(fbb.GetBufferPointer(), fbb.GetSize());\n"
        s += "}\n\n"

        # deserializeFbs
        h += "vector<char> deserializeFbs(const std::vector<char>& data);\n"
        s += "\nvector<char> " + table_name + "::deserializeFbs(const std::vector<char>& data) {\n"
        s += "  auto fb = Get" + fbs_root_type + "(data.data());\n"
        s += "  auto result = new " + fbs_root_type + "();\n"
        s += "  (*result) = fb;\n"
        s += "  return result;\n"
        s += "}\n\n"

    nss = namespace.split('.')
    nss.reverse()
    for ns in nss:
        h += "} // namespace %s\n" % ns
        s += "} // namespace %s\n" % ns
    return (h, s)

def generate_schema():
    global fbs_data

    schemas = OrderedDict()
    for table_type, table in fbs_data.iteritems():
        schemas[table_type] = []
        for item_name, item in table.iteritems():
            s = OrderedDict()
            s['name']      = item_name
            s['type']      = item['item_type']
            s['attribute'] = item['attribute']
            s['is_vector'] = True if item['is_vector'] else False
            schemas[table_type].append(s)
    return json.dumps(schemas, indent=2)

# ---
# main function
#
if __name__ == '__main__':
    logging.basicConfig(level = logging.INFO, format = '%(asctime)-15s %(levelname)s %(message)s')

    parser = argparse.ArgumentParser(description = 'convert fbs schema to C++ classes')
    parser.add_argument('input_fbs',     metavar = 'input.fbs',   help = 'input FlatBuffers schema file')
    parser.add_argument('output_header', metavar = 'output.h',    help = 'output class header file (C++ header)')
    parser.add_argument('output_body',   metavar = 'output.cpp',  help = 'output class file (C++)')
    parser.add_argument('output_schema', metavar = 'output.json', help = 'output schema file (json)')
    parser.add_argument('--namespace',  help = 'name space override')
    parser.add_argument('--json',    action = 'store_true', default = True,  help = 'generate json IO code')
    parser.add_argument('--msgpack', action = 'store_true', default = True,  help = 'generate msgpack IO code')
    parser.add_argument('--fbs',     action = 'store_true', default = False, help = 'generate flatbuffers IO code')
    args = parser.parse_args()

    info("input  = %s" % args.input_fbs)
    info("output header = %s" % args.output_header)
    info("output body = %s" % args.output_body)
    info("output schema = %s" % args.output_schema)
    info("namespace = %s" % args.namespace)
    info("with json = %s" % args.json)
    info("with msgpack = %s" % args.msgpack)
    info("with fbs = %s" % args.fbs)
    fbs2class(args.input_fbs, args.output_header, args.output_body, args.output_schema, args.namespace, args.json, args.msgpack, args.fbs)
    exit(0)


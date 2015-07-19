#! /usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function
import sys
import re
import argparse
import logging
import json

from logging import info, warning, error
from collections import OrderedDict

def fbs2class(input_fbs, output_class, output_schema, namespace, with_json, with_msgpack, with_fbs):
    with open(input_fbs, 'r') as f:
        global state, fbs_data
        state = "default"
        fbs_data = OrderedDict({})
        for line in f:
            if state == "default":
                parse_default(line)
            elif state == "table":
                parse_table(line)

    # write user_data.h
    cls = generate_classes(namespace, with_json, with_msgpack, with_fbs)
    with open(output_class, 'w') as f:
        f.write(cls)

    # write user_schema.json
    json = generate_schema()
    with open(output_schema, 'w') as f:
        f.write(json)

def parse_default(line):
    global state
    global fbs_data
    global fbs_root_type
    global fbs_namespace
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
    m = re.search('\s*([^:]+):\s*\[([^;]+)\];', line)
    if m != None:
        name = m.group(1)
        type = m.group(2)
        is_vector = True
    else:
        m = re.search('\s*([^:]+):\s*([^;]+);', line)
        if m == None:
            return
        name = m.group(1)
        type = m.group(2)
        is_vector = False
    m = re.search('([^\s\(]+)\s*\(([^\)]+)\)\s*', type)
    if m:
        type = m.group(1)
        attribute = OrderedDict()
        for attr_str in re.split('[,\s]+', m.group(2)):
            attrs = re.split('[:\s]+', attr_str)
            print(attrs)
            if len(attrs) > 1:
                attribute[attrs[0]] = ':'.join(attrs[1:])
            else:
                attribute[attrs[0]] = True
            if 'hash' in attrs:
                is_hash_key = True
            elif 'key' in attrs:
                is_range_key = True

    item = OrderedDict(
        name = name,
        type = type,
        item_type = type,
        attribute = attribute,
        is_vector = is_vector,
        is_hash_key = is_hash_key,
        is_range_key = is_range_key
    )

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

    s = ''
    s += '#include <iomanip>\n'
    s += '#include <sstream>\n'
    s += '#include <jansson.h>\n'
    s += '#include <format.h>\n'
    s += '#include <openssl/md5.h>\n'
    s += '#include <cocos2d.h>\n'
    if with_msgpack:
        s += '#include <msgpack.hpp>\n'
    if with_fbs:
        s += '#include "user_data_generated.h"\n'
    s += "\n"

    s += '#pragma clang diagnostic ignored "-Wc++11-extensions"\n'
    s += '#pragma clang diagnostic ignored "-Wunused-variable"\n'
    s += "\n"

    namespace = namespace or fbs_namespace
    for ns in namespace.split('.'):
        s += "namespace " + ns + " {\n"

    s += "\n// class prototypes\n"
    for table_name in fbs_data:
        s += "class " + table_name + ";\n"

    s += "\n// calcurate MD5 checksum\n"
    s += "static std::string calcChecksum(const unsigned char* data, size_t len) {\n"
    s += "  unsigned char buf[MD5_DIGEST_LENGTH];\n"
    s += "  MD5(data, len, buf);\n"
    s += "  std::stringstream hex;\n"
    s += "  hex << std::hex << std::nouppercase << std::setfill('0');\n"
    s += "  for (int i = 0; i < MD5_DIGEST_LENGTH; i++) {\n"
    s += "    hex << std::setw(2) << (unsigned short)buf[i];\n"
    s += "  }\n"
    s += "  return hex.str();\n"
    s += "}\n"

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
            if item["item_type"] == "string":
                item["cpp_type"] = "std::string"
            elif item["is_default_type"]:
                item["cpp_type"] = item["item_type"]
            else:
                item["cpp_type"] = "std::shared_ptr<" + item["item_type"] + ">"

    # main generating
    s += "\n// main class definitions\n"
    for table_name in fbs_data:
        table = fbs_data[table_name]
        prop  = table_property[table_name]

        s += "class " + table_name + " {\n protected:\n"
        for item_name, item in table.iteritems():
            if item["is_vector"]:
                s += "  std::vector<" + item["cpp_type"] + " > _" + item_name + ";\n"
                s += "  std::vector<" + item["cpp_type"] + " > _" + item_name + "Erased;\n"
                range_key = get_item_range_key(item, fbs_data, table_property)
                if range_key:
                    s += "  std::map<" + range_key["cpp_type"] + ", " + item["cpp_type"] + " > _" + item_name + "Map;\n"
            else:
                s += "  " + item["cpp_type"] + " _" + item_name + ";\n"
        s += "\n"
        s += "  time_t __timestamp;  // timestamp of sync or flush (internal use)\n"
        s += "  bool __dirty; // dirty flag to detect this record is modified (internal use)\n"

        s += "\n public:\n"
        s += "  // constructer\n"
        inits = []
        for item_name, item in table.iteritems():
            if not item["is_default_type"] and not item["is_vector"]:
                inits.append("    _" + item_name + "(std::make_shared<" + item["item_type"] + " >()),\n")
        s += "  " + table_name + "() : \n" + "".join(inits) + "    __timestamp(0), __dirty(true) {}\n"

        s += "\n  // getters\n"
        for item_name, item in table.iteritems():
            if item["is_vector"]:
                s += "  const std::vector<" + item["cpp_type"] + " >* " + item_name + "() const { return &_" + item_name + "; }\n"
                range_key = get_item_range_key(item, fbs_data, table_property)
                if range_key:
                    s += "  " + item["cpp_type"]+ " lookup" + upper_camel_case(item_name) + "(" + range_key["cpp_type"] + " needle) {\n"
                    s += "    return _" + item_name + "Map.at(needle);\n"
                    s += "  }\n"
            else:
                s += "  " + item["cpp_type"] + " " + item_name + "() const { return _" + item_name + "; }\n"

        s += "\n  // setters\n"
        for item_name, item in table.iteritems():
            s += "  // setter for " + item_name + "\n"
            if item["is_vector"]:
                range_key = get_item_range_key(item, fbs_data, table_property)
                if range_key:
                    s += "  void set" + upper_camel_case(item_name) + "(int pos, const " + item["cpp_type"] + "& value) {\n"
                    s += "    if (_" + item_name + "[pos]) _" + item_name + "Map.erase(_" + item_name + "[pos]->" + range_key["name"] + "());\n"
                    s += "    _" + item_name + "Map[value->" + range_key["name"] + "()] = value;\n"
                    s += "    _" + item_name + "[pos] = value;\n"
                    s += "    __dirty = true;\n"
                    s += "  }\n"
                else:
                    s += "  void set" + upper_camel_case(item_name) + "(int pos, const " + item["cpp_type"] + "& value, const " + item["cpp_type"] + "& defaultValue) {\n"
                    s += "    if (_" + item_name + ".capacity() <= pos) {\n"
                    s += "      _" + item_name + ".resize(pos + 1, defaultValue);\n"
                    s += "    }\n"
                    s += "    _" + item_name + "[pos] = value;\n"
                    s += "    __dirty = true;\n"
                    s += "  }\n"
                s += "  void emplace" + upper_camel_case(item_name) + "(std::vector<" + item["cpp_type"] + " >::const_iterator pos, const " + item["cpp_type"] + "& value) {\n"
                s += "    _" + item_name + ".emplace(pos, value);\n"
                if range_key:
                    s += '    CCASSERT(_' + item_name + 'Map.find(value->' + range_key["name"] + '()) == _' + item_name + 'Map.end(), fmt::format("duplicated range key in ' + item_name + ': {}", value->' + range_key["name"] + '()).c_str());\n'
                    s += "    _" + item_name + "Map[value->" + range_key["name"] + "()] = value;\n"
                s += "    __dirty = true;\n"
                s += "  }\n"
                s += "  void insert" + upper_camel_case(item_name) + "(std::vector<" + item["cpp_type"] + " >::const_iterator pos, const " + item["cpp_type"] + "& value) {\n"
                s += "    _" + item_name + ".insert(pos, value);\n"
                if range_key:
                    s += '    CCASSERT(_' + item_name + 'Map.find(value->' + range_key["name"] + '()) == _' + item_name + 'Map.end(), fmt::format("duplicated range key in ' + item_name + ': {}", value->' + range_key["name"] + '()).c_str());\n'
                    s += "    _" + item_name + "Map[value->" + range_key["name"] + "()] = value;\n"
                s += "    __dirty = true;\n"
                s += "  }\n"
                s += "  void pushBack" + upper_camel_case(item_name) + "(const " + item["cpp_type"] + "& value) {\n"
                s += "    _" + item_name + ".push_back(value);\n"
                if range_key:
                    s += '    CCASSERT(_' + item_name + 'Map.find(value->' + range_key["name"] + '()) == _' + item_name + 'Map.end(), fmt::format("duplicated range key in ' + item_name + ': {}", value->' + range_key["name"] + '()).c_str());\n'
                    s += "    _" + item_name + "Map[value->" + range_key["name"] + "()] = value;\n"
                s += "    __dirty = true;\n"
                s += "  }\n"
                s += "  void erase" + upper_camel_case(item_name) + "(std::vector<" + item["cpp_type"] + " >::const_iterator pos) {\n"
                s += "    auto erased = _" + item_name + ".erase(pos);\n"
                s += "    _" + item_name + "Erased.push_back(*erased);\n"
                if range_key:
                    s += "    _" + item_name + "Map.erase((*pos)->" + range_key["name"] + "());\n"
                s += "    // __dirty = true; // erase is not dirty\n"
                s += "  }\n"
                s += "  void clear" + upper_camel_case(item_name) + "() {\n"
                s += "    for (auto __v : _" + item_name + ") {\n"
                s += "      _" + item_name + "Erased.push_back(__v);\n"
                s += "    }\n"
                s += "    _" + item_name + ".clear();\n"
                if range_key:
                    s += "    _" + item_name + "Map.clear();\n"
                s += "    // __dirty = true; // erase is not dirty\n"
                s += "  }\n"
            elif item["is_default_type"]:
                s += "  void set" + upper_camel_case(item_name) + "(" + item["cpp_type"] + " value) { \n"
                s += "    _" + item_name + " = value;\n"
                s += "    __dirty = true;\n"
                s += "  }\n"
                if item["item_type"] == 'string':
                    s += "  void set" + upper_camel_case(item_name) + "(const char* value) {\n"
                    s += "    _" + item_name + " = value;\n"
                    s += "    __dirty = true;\n"
                    s += "  }\n"

        s += "\n  // dirty flag\n"
        s += "  bool isDirty() const {\n"
        s += "    return __dirty;\n"
        s += "  }\n"
        s += "  bool isDirtyRecursive() {\n"
        s += "    if (__dirty) return true;\n"
        for item_name, item in table.iteritems():
            if not item["is_default_type"] and item["is_vector"]:
                s += "    for (auto it = _" + item_name + ".begin(); it != _" + item_name + ".end(); it++) {\n"
                s += "      if ((*it)->isDirtyRecursive()) {\n"
                s += "        __dirty = true;  // bump up to parent\n"
                s += "        return true;\n"
                s += "      }\n"
                s += "    }\n"
            elif not item["is_default_type"]:
                s += "    if (_" + item_name + "->isDirtyRecursive()) {\n"
                s += "      __dirty = true;  // bump up to parent\n"
                s += "      return true;\n"
                s += "    }\n"
        s += "    return false;\n"
        s += "  }\n"
        s += "  void clearDirty() {\n"
        s += "    __dirty = false;\n"
        s += "  }\n"
        s += "  void clearDirtyRecursive() {\n"
        for item_name, item in table.iteritems():
            if not item["is_default_type"] and item["is_vector"]:
                s += "    for (auto it = _" + item_name + ".begin(); it != _" + item_name + ".end(); it++) {\n"
                s += "      (*it)->clearDirtyRecursive();\n"
                s += "    }\n"
            elif not item["is_default_type"]:
                s += "    _" + item_name + "->clearDirtyRecursive();\n"
        s += "    __dirty = false;\n"
        s += "  }\n"

        s += "\n  // general accessor\n"
        if fbs_root_type == table_name:
            s += "  std::vector<std::string> keys() {\n"
            s += "    std::vector<std::string> _keys;\n"
            for item_name in table:
                s += '    _keys.push_back("' + item_name + '");\n'
            s += "    return _keys;\n"
            s += "  }\n"
            s += "  std::vector<std::string> tables() {\n"
            s += "    std::vector<std::string> _tables;\n"
            for item_name, item in table.iteritems():
                s += '    _tables.push_back("' + item["item_type"] + '");\n'
            s += "    return _tables;\n"
            s += "  }\n"
            s += "  const char* getTableName(const std::string& target) {\n"
            for item_name, item in table.iteritems():
                s += '    if (target == "' + item_name + '") return "' + item["item_type"] + '";\n'
            s += '    return "";\n'
            s += "  }\n"
            s += "  std::vector<int> collectRangeKey(const std::string& target) {\n"
            s += '    std::vector<int> rangeKeys;\n'
            for item_name, item in table.iteritems():
                if not "range_key" in table_property[item["item_type"]]:
                    continue
                s += '    if (target == "' + item_name + '") {\n'
                if item["is_vector"]:
                    s += "      for (auto it = _" + item_name + ".begin(); it != _" + item_name + ".end(); it++) {\n"
                    s += "        rangeKeys.push_back((*it)->rangeKeyValue());\n"
                    s += "      }\n"
                else:
                    s += '      rangeKeys.push_back(_' + item_name + '->rangeKeyValue());\n'
                s += '      return rangeKeys;\n'
                s += '    }\n'
            s += '    return rangeKeys;\n'
            s += '  }\n'
            s += "  std::vector<int> collectErasedRangeKey(const std::string& target) {\n"
            s += '    std::vector<int> rangeKeys;\n'
            for item_name, item in table.iteritems():
                if not "range_key" in table_property[item["item_type"]]:
                    continue
                s += '    if (target == "' + item_name + '") {\n'
                if item["is_vector"]:
                    s += "      for (auto it = _" + item_name + "Erased.begin(); it != _" + item_name + "Erased.end(); it++) {\n"
                    s += "        rangeKeys.push_back((*it)->rangeKeyValue());\n"
                    s += "      }\n"
                s += '      return rangeKeys;\n'
                s += '    }\n'
            s += '    return rangeKeys;\n'
            s += '  }\n'

        if "hash_key" in prop:
            hash_key = prop["hash_key"]
            s += "  const char* hashKey() const {\n"
            s += '    return "' + hash_key + '";\n'
            s += "  }\n"
            s += "  const " + table[hash_key]["cpp_type"] + " hashKeyValue() const {\n"
            s += "    return _" + hash_key + ";\n"
            s += "  }\n"
            s += "  long setHashKey(long v) {\n"
            s += "    if (v != _" + hash_key + ") {\n"
            s += "      _" + hash_key + " = v;\n" 
            s += "      __dirty = true;\n"
            s += "    }\n"
            s += "    return v;\n"
            s += "  }\n"
        if "range_key" in prop:
            range_key = prop["range_key"]
            s += "  const char* rangeKey() const {\n"
            s += '    return "' + range_key + '";\n'
            s += "  }\n"
            s += "  const " + table[range_key]["cpp_type"] + " rangeKeyValue() const {\n"
            s += "    return _" + range_key + ";\n"
            s += "  }\n"
            s += "  int setRangeKey(int v) {\n"
            s += "    if (!_" + range_key + ") {\n"
            s += "      _" + range_key + " = v++;\n" 
            s += "      __dirty = true;\n"
            s += "    }\n"
            s += "    return v;\n"
            s += "  }\n"
        s += "  int completeKey(long hashKey, int rangeKey) {\n"
        for item_name, item in table.iteritems():
            if item["is_hash_key"]:
                s += "    setHashKey(hashKey);\n"
            elif item["is_range_key"]:
                s += "    rangeKey = setRangeKey(rangeKey);\n"
            elif not item["is_default_type"] and "range_key" in table_property[item["item_type"]]:
                if item["is_vector"]:
                    s += "    for (auto it = _" + item_name + ".begin(); it != _" + item_name + ".end(); it++) {\n"
                    s += "      rangeKey = (*it)->completeKey(hashKey, rangeKey);\n"
                    s += "    }\n"
                else:
                    s += "    rangeKey = _" + item_name + "->completeKey(hashKey, rangeKey);\n"
        s += "    return rangeKey;\n"
        s += "  }\n"

        if with_json:
            s += "\n  // getter via json\n"
            s += "  json_t* toJson(bool onlyDirty) {\n"
            s += "    if (onlyDirty && !isDirty()) return nullptr;\n"
            s += "    auto json = json_object();\n"
            for item_name, item in table.iteritems():
                item_type = item["item_type"]
                if item["is_vector"]:
                    s += "    auto a_" + item_name + " = json_array();\n"
                    s += "    for (auto it = _" + item_name + ".begin(); it != _" + item_name + ".end(); it++) {\n"
                    if item_type == 'string':
                        s += "      json_array_append(a_" + item_name + ", json_string((*it).c_str()));\n"
                    elif item_type in ('int', 'long'):
                        s += "      json_array_append(a_" + item_name + ", json_integer(*it));\n"
                    elif item_type in ('float', 'double'):
                        s += "      json_array_append(a_" + item_name + ", json_real(*it));\n"
                    elif item_type in ('bool'):
                        s += "      json_array_append(a_" + item_name + ", json_boolean(*it));\n"
                    else:
                        s += "      json_array_append(a_" + item_name + ", (*it)->toJson(onlyDirty));\n"
                    s += "    }\n"
                    s += '    json_object_set_new(json, "' + item_name + '", a_' + item_name + ');\n'
                elif item_type == 'string':
                    s += '    json_object_set_new(json, "' + item_name + '", json_string(_' + item_name + '.c_str()));\n'
                elif item_type in ('int', 'long'):
                    s += '    json_object_set_new(json, "' + item_name + '", json_integer(_' + item_name + '));\n'
                elif item_type in ('float', 'double'):
                    s += '    json_object_set_new(json, "' + item_name + '", json_real(_' + item_name + '));\n'
                elif item_type in ('bool'):
                    s += '    json_object_set_new(json, "' + item_name + '", json_boolean(_' + item_name + '));\n'
                else:
                    s += '    json_object_set_new(json, "' + item_name + '", _' + item_name + '->toJson(onlyDirty));\n'
            s += "    return json;\n";
            s += "  }\n"

            s += "\n  // setter via json\n"
            s += "  void fromJson(json_t* json) {\n"
            if "has_vector" in prop:
                s += "    int i;\n"
                s += "    json_t* v;\n"
            for item_name, item in table.iteritems():
                item_type = item["item_type"]
                range_key = get_item_range_key(item, fbs_data, table_property)
                s += '    auto __' + item_name + ' = json_object_get(json, "' + item_name + '");\n'
                s += '    if (__' + item_name + ') {\n'
                if item["is_vector"]:
                    s += "      _" + item_name + ".clear();\n"
                    if range_key:
                        s += "      _" + item_name + "Map.clear();\n"
                    s += '      json_array_foreach(__' + item_name + ', i, v) {\n'
                    if item_type in ('string'):
                        s += "        pushBack" + upper_camel_case(item_name) + "(json_string_value(v));\n"
                    elif item_type in ('int', 'long'):
                        s += "        pushBack" + upper_camel_case(item_name) + "(json_integer_value(v));\n"
                    elif item_type in ('float', 'double'):
                        s += "        pushBack" + upper_camel_case(item_name) + "(json_real_value(v));\n"
                    elif item_type in ('bool'):
                        s += "        pushBack" + upper_camel_case(item_name) + "(json_boolean_value(v));\n"
                    else:
                        s += "        pushBack" + upper_camel_case(item_name) + "(std::make_shared<" + item["item_type"] + " >(v));\n"
                    s += "      }\n"
                elif item_type in ('string'):
                    s += "      set" + upper_camel_case(item_name) + '(json_string_value(__' + item_name + '));\n'
                elif item_type in ('int', 'long'):
                    s += "      set" + upper_camel_case(item_name) + '(json_integer_value(__' + item_name + '));\n'
                elif item_type in ('float', 'double'):
                    s += "      set" + upper_camel_case(item_name) + '(json_real_value(__' + item_name + '));\n'
                elif item_type in ('bool'):
                    s += "      set" + upper_camel_case(item_name) + '(json_boolean_value(__' + item_name + '));\n'
                else:
                    s += "      _" + item_name + '->fromJson(__' + item_name + ');\n'
                s += '    }\n'
            s += "    clearDirty();\n"
            s += "  }\n"
            s += "  // construct with json\n"
            s += "  " + table_name + "(json_t* json) {\n"
            s += "    fromJson(json);\n"
            s += "  }\n"

        if with_msgpack:
            s += "\n  // getter via msgpack\n"
            s += "  void toMsgpack(msgpack::packer<msgpack::sbuffer>& pk) {\n"
            s += "    pk.pack_map(%d);\n" % len(table)
            for item_name, item in table.iteritems():
                s += '    pk.pack(std::string("' + item_name + '"));\n'
                if item["is_vector"]:
                    s += '    pk.pack_array((int)_' + item_name + '.size());\n'
                    s += '    for (auto it = _' + item_name + '.begin(); it != _' + item_name + '.end(); it++) {\n'
                    if item["item_type"] == "bool":
                        s += '      pk.pack(*it ? true : false);\n'
                    elif item["is_default_type"]:
                        s += '      pk.pack(*it);\n'
                    else:
                        s += '      (*it)->toMsgpack(pk);\n'
                    s += '    }\n'
                elif item["item_type"] == "bool":
                    s += '    pk.pack(_' + item_name + ' ? true : false);\n'
                elif item["is_default_type"]:
                    s += '    pk.pack(_' + item_name + ');\n'
                else:
                    s += '    _' + item_name + '->toMsgpack(pk);\n'
            s += "  }\n"

            s += "\n  // setter via msgpack\n"
            s += "  void fromMsgpack(msgpack::object& obj) {\n"
            s += "    std::map<std::string, msgpack::object> __map = obj.as<std::map<std::string, msgpack::object> >();\n"
            for item_name, item in table.iteritems():
                range_key = get_item_range_key(item, fbs_data, table_property)
                s += '    auto __v_' + item_name + ' = __map.find("' + item_name + '");\n'
                s += '    if (__v_' + item_name + ' != __map.end()) {\n'
                if item["is_vector"]:
                    s += "      _" + item_name + ".clear();\n"
                    if range_key:
                        s += "      _" + item_name + "Map.clear();\n"
                    s += '      auto __' + item_name + ' = __v_' + item_name + '->second.as<msgpack::object>();\n';
                    s += '      for (msgpack::object* p(__' + item_name + '.via.array.ptr), * const pend(__' + item_name + '.via.array.ptr + __' + item_name + '.via.array.size); p < pend; ++p) {\n'
                    if item["is_default_type"]:
                        s += '        pushBack' + upper_camel_case(item_name) + '(p->as<' + item["cpp_type"] + '>());\n'
                    else:
                        s += '        pushBack' + upper_camel_case(item_name) + '(std::make_shared<' + item["item_type"] + ' >(*p));\n'
                    s += '      }\n'
                elif item["is_default_type"]:
                    s += '      set' + upper_camel_case(item_name) + '(__v_' + item_name + '->second.as<' + item["cpp_type"] + ' >());\n'
                else:
                    s += '      _' + item_name + '->fromMsgpack(__v_' + item_name + '->second);\n'
                s += '    }\n'
            s += "    clearDirty();\n"
            s += "  }\n"
            s += "  // construct with json\n"
            s += "  " + table_name + "(msgpack::object& obj) {\n"
            s += "    fromMsgpack(obj);\n"
            s += "  }\n"

        if with_json and fbs_root_type == table_name:
            s += "\n  // top level of JSON IO\n"
            s += "  json_t* serializeJson(const std::string& target, bool onlyDirty) {\n"
            for item_name, item in table.iteritems():
                s += '    if (target == "' + item_name + '") {\n'
                if item["is_vector"]:
                    s += '      auto a_' + item_name + ' = json_array();\n'
                    s += '      for (auto it = _' + item_name + '.begin(); it != _' + item_name + '.end(); it++) {\n'
                    s += '        if (onlyDirty && !(*it)->isDirtyRecursive()) continue;\n'
                    s += '        auto __j = (*it)->toJson(onlyDirty);\n'
                    s += '        if (__j != nullptr) json_array_append(a_' + item_name + ', __j);\n'
                    s += '      }\n'
                    s += '      return (!onlyDirty || json_array_size(a_' + item_name +') > 0) ? a_' + item_name +' : json_null();\n'
                else:
                    s += '      if (onlyDirty && !_' + item_name + '->isDirtyRecursive()) return json_null();\n'
                    s += '      return _' + item_name + '->toJson(onlyDirty);\n'
                s += '    }\n'
            s += "    return json_null();\n"
            s += "  }\n"
            s += "  void deserializeJson(json_t* json, const std::string& target) {\n"
            if "has_vector" in prop:
                s += "    int i;\n"
                s += "    json_t* v;\n"
            for item_name, item in table.iteritems():
                s += '    if (target == "' + item_name + '") {\n'
                if item["is_vector"]:
                    s += "      _" + item_name + ".clear();\n"
                    s += "      json_array_foreach(json, i, v) {\n"
                    s += "        auto __" + item_name + " = std::make_shared<" + item["item_type"] + ">();\n"
                    s += "        __" + item_name + "->fromJson(v);\n"
                    s += "        pushBack" + upper_camel_case(item_name) + "(__" + item_name + ");\n"
                    s += '      }\n'
                else:
                    s += '      _' + item_name + '->fromJson(json);\n'
                s += '      return;\n'
                s += '    }\n'
            s += "  }\n"

        if with_msgpack and fbs_root_type == table_name:
            s += "\n  // top level of msgpack IO\n"
            s += "  void serializeMsgpack(msgpack::packer<msgpack::sbuffer>& pk, const std::string& target) {\n"
            for item_name, item in table.iteritems():
                s += '    if (target == "' + item_name + '") {\n'
                if item["is_vector"]:
                    s += '      pk.pack_array((int)_' + item_name + '.size());\n'
                    s += '      for (auto it = _' + item_name + '.begin(); it != _' + item_name + '.end(); it++) {\n'
                    s += '        (*it)->toMsgpack(pk);\n'
                    s += '      }\n'
                else:
                    s += '      _' + item_name + '->toMsgpack(pk);\n'
                s += '      return;\n'
                s += '    }\n'
            s += "  }\n"
            s += "  void deserializeMsgpack(msgpack::object& obj, const std::string& target) {\n"
            for item_name, item in table.iteritems():
                s += '    if (target == "' + item_name + '") {\n'
                if item["is_vector"]:
                    s += '      for (msgpack::object* p(obj.via.array.ptr), * const pend(obj.via.array.ptr + obj.via.array.size); p < pend; ++p) {\n'
                    s += '        auto __' + item_name + ' = std::make_shared<' + item["item_type"] + '>();\n'
                    s += '        __' + item_name + '->fromMsgpack(*p);\n'
                    s += "        pushBack" + upper_camel_case(item_name) + "(__" + item_name + ");\n"
                    s += '      }\n'
                else:
                    s += '      _' + item_name + '->fromMsgpack(obj);\n'
                s += '      return;\n'
                s += '    }\n'
            s += "  }\n"

        if with_fbs:
            s += "\n  // for FlatBuffers\n"
            # FIXME treat fbs::
            s += "  flatbuffers::Offset<fbs::" + table_name + "> to_flatbuffers(flatbuffers::FlatBufferBuilder *fbb) {\n"
            for item_name, item in table.iteritems():
                if item["is_vector"]:
                    s += "    // vector of " + item_name + "\n";
                    s += "    std::vector<" + item["cpp_type"] + " __" + item_name + ";\n"
                    s += "    for (auto it = _" + item_name + ".begin(); it != _" + item_name + ".end(); it++) {\n"
                    if item["item_type"] == 'string':
                        s += "      __" + item_name + "->pushBack" + upper_camel_case(item_name) + "(fbb->CreateString(*it));\n"
                    elif item["is_default_type"]:
                        s += "      __" + item_name + "->pushBack" + upper_camel_case(item_name) + "(*it);\n"
                    else:
                        s += "      __" + item_name + "->pushBack" + upper_camel_case(item_name) + "((*it)->to_flatbuffers(fbb));\n"
                    s += "    }\n"
                    s += "    auto fb_" + item_name + " = fbb->CreateVector(__" + item_name + ");\n"
                elif item["item_type"] == 'string':
                    s += "    auto fb_" + item_name + " = fbb->CreateString(_" + item_name + ");\n"
                elif item["is_default_type"]:
                    s += "    auto fb_" + item_name + " = _" + item_name + ";\n"
                else:
                    s += "    auto fb_" + item_name + " = _" + item_name + "->to_flatbuffers(fbb);\n"
            s += "    return fbs::Create" + upper_camel_case(table_name) + "(*fbb,\n"
            remains = len(table)
            for item_name, item in table.iteritems():
                s += "      fb_" + item_name
                remains -= 1
                if remains == 0:
                    s += ");\n"
                else:
                    s += ",\n"
            s += "  }\n"

        s += "\n  // calcurate MD5 checksum\n"
        s += "  std::string checksum() {\n"
        if with_msgpack:
            s += "    msgpack::sbuffer sbuf;\n"
            s += "    msgpack::packer<msgpack::sbuffer> pk(&sbuf);\n"
            s += "    toMsgpack(pk);\n"
            s += "    return " + "::".join(namespace.split('.')) + "::calcChecksum(reinterpret_cast<const unsigned char*>(sbuf.data()), sbuf.size());\n"
        elif with_json:
            s += "    std::string data = json_dumps(toJson(), JSON_COMPACT | JSON_ENCODE_ANY);\n"
            s += "    return " + "::".join(namespace.split('.')) + "::calcChecksum(reinterpret_cast<const unsigned char*>(data.c_str()), data.length());\n"
        else:
            s += '    std::string data("no available format");\n'
        s += "  }\n"

        # end of class
        s += "};\n\n" 

    if with_fbs:
        s += "std::vector<char> serializeFbs() {\n"
        s += "  flatbuffers::FlatBufferBuilder fbb;\n"
        s += "  auto data = " + fbs_root_type + ".to_flatbuffers(&fbb);\n"
        s += "  fbb.Finish(data);\n"
        s += "  return std::vector<char>(fbb.GetBufferPointer(), fbb.GetSize());\n"
        s += "}\n\n"

        s += "vector<char> deserializeFbs(const std::vector<char>& data) {\n"
        s += "  auto fb = Get" + fbs_root_type + "(data.data());\n"
        s += "  auto result = new " + fbs_root_type + "();\n"
        s += "  (*result) = fb;\n"
        s += "  return result;\n"
        s += "}\n\n"

    nss = namespace.split('.')
    nss.reverse()
    for ns in nss:
        s += "} // namespace %s\n" % ns
    return s

def generate_schema():
    global fbs_data

    schemas = OrderedDict()
    for table_name, table in fbs_data.iteritems():
        schemas[table_name] = []
        for item_name, item in table.iteritems():
            s = OrderedDict()
            s['name']         = item_name
            s['type']         = item['item_type']
            s['attribute']    = item['attribute']
            s['is_hash_key']  = True if item['is_hash_key']  else False
            s['is_range_key'] = True if item['is_range_key'] else False
            s['is_vector']    = True if item['is_vector']    else False
            schemas[table_name].append(s)
    return json.dumps(schemas, indent=2)

# ---
# main function
#
if __name__ == '__main__':
    logging.basicConfig(level = logging.INFO, format = '%(asctime)-15s %(levelname)s %(message)s')

    parser = argparse.ArgumentParser(description = 'convert fbs schema to C++ classes')
    parser.add_argument('input_fbs',     metavar = 'input.fbs',   help = 'input FlatBuffers schema file')
    parser.add_argument('output_class',  metavar = 'output.h',    help = 'output class file (C++ header)')
    parser.add_argument('output_schema', metavar = 'output.json', help = 'output schema file (json)')
    parser.add_argument('--namespace',  help = 'name space override')
    parser.add_argument('--json',    action = 'store_true', default = True,  help = 'generate json IO code')
    parser.add_argument('--msgpack', action = 'store_true', default = True,  help = 'generate msgpack IO code')
    parser.add_argument('--fbs',     action = 'store_true', default = False, help = 'generate flatbuffers IO code')
    args = parser.parse_args()

    info("input  = %s" % args.input_fbs)
    info("output = %s" % args.output_class)
    info("namespace = %s" % args.namespace)
    info("with json = %s" % args.json)
    info("with msgpack = %s" % args.msgpack)
    info("with fbs = %s" % args.fbs)
    fbs2class(args.input_fbs, args.output_class, args.output_schema, args.namespace, args.json, args.msgpack, args.fbs)
    exit(0)


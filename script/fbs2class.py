#! /usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function
import sys
import re
import argparse
import logging

from logging import info, warning, error
from collections import OrderedDict

def fbs2class(fbs, dst, namespace, with_json, with_msgpack, with_fbs):
    with open(fbs, 'r') as f:
        global state, fbs_data
        state = "default"
        fbs_data = OrderedDict({})
        for line in f:
            if state == "default":
                parse_default(line)
            elif state == "table":
                parse_table(line)
    generate_classes(dst, namespace, with_json, with_msgpack, with_fbs)

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

    # preprocess in comment
    is_hash_key  = re.search('<hash.key>', line)
    is_range_key = re.search('<range.key>', line)
    line = re.sub('\/\/.*', '', line)   # cut comment

    # main parse
    m = re.search('\s*\}', line)
    if m != None:
        state = "default"
        return
    m = re.search('\s*([^:]+):\[([^;]+)\];', line)
    if m != None:
        name = m.group(1)
        item = {'is_vector':True, 'item_type':m.group(2)}
    else:
        m = re.search('\s*([^:]+):([^;]+);', line)
        if m == None:
            return
        name = m.group(1)
        item = {'is_vector':False, 'item_type':m.group(2)}
    item['is_hash_key']  = is_hash_key
    item['is_range_key'] = is_range_key

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

def generate_classes(dst, namespace=None, with_json=True, with_msgpack=True, with_fbs=False):
    global fbs_data
    global fbs_root_type
    global fbs_namespace

    s = ''
    s += '#include <iomanip>\n'
    s += '#include <sstream>\n'
    s += '#include <jansson.h>\n'
    s += '#include <openssl/md5.h>\n'
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

    s += "\n// main class definitions\n"
    for table_name in fbs_data:
        table = fbs_data[table_name]

        hash_key   = None
        range_key  = None
        has_vector = False
        for item_name, item in table.iteritems():
            if item["is_vector"]:
                has_vector = True
            if item["is_hash_key"]:
                hash_key  = item_name
            if item["is_range_key"]:
                range_key = item_name

            item["is_default_type"] = not item["item_type"] in fbs_data
            if item["item_type"] == "string":
                item["cpp_type"] = "std::string"
            elif item["is_default_type"]:
                item["cpp_type"] = item["item_type"]
            else:
                item["cpp_type"] = "std::shared_ptr<" + item["item_type"] + ">"

        s += "class " + table_name + " {\n protected:\n"
        for item_name, item in table.iteritems():
            if item["is_vector"]:
                s += "  std::vector<" + item["cpp_type"] + " > _" + item_name + ";\n"
            else:
                s += "  " + item["cpp_type"] + " _" + item_name + ";\n"
        s += "\n"
        s += "  time_t __timestamp;  // timestamp of sync or flush (internal use)\n"

        s += "\n public:\n"
        s += "  // constructer\n"
        inits = []
        for item_name, item in table.iteritems():
            if not item["is_default_type"] and not item["is_vector"]:
                inits.append("    _" + item_name + "(std::make_shared<" + item["item_type"] + " >()),\n")
        s += "  " + table_name + "() : \n" + "".join(inits) + "    __timestamp(0) {}\n"

        s += "\n  // getter\n"
        for item_name, item in table.iteritems():
            if item["is_vector"]:
                s += "  std::vector<" + item["cpp_type"] + " >* " + item_name + "() { return &_" + item_name + "; }\n"
            else:
                s += "  " + item["cpp_type"] + " " + item_name + "() { return _" + item_name + "; }\n"

        s += "\n  // setter\n"
        for item_name, item in table.iteritems():
            if item["is_default_type"] and not item["is_vector"]:
                s += "  void set" + upper_camel_case(item_name) + "(" + item["cpp_type"] + " value) { _" + item_name + " = value; }\n"
                if item["item_type"] == 'string':
                    s += "  void set" + upper_camel_case(item_name) + "(const char* value) { _" + item_name + " = value; }\n"

        s += "\n  // general accessor\n"
        if fbs_root_type == table_name:
          s += "  std::vector<std::string> keys() {\n"
          s += "    std::vector<std::string> _keys;\n"
          for item_name in table:
              s += '    _keys.push_back("' + item_name + '");\n'
          s += "    return _keys;\n"
          s += "  }\n"

        if hash_key:
            s += "  const char* hashKey() const {\n"
            s += '    return "' + hash_key + '";\n'
            s += "  }\n"
            s += "  const " + table[hash_key]["cpp_type"] + " hashKeyValue() const {\n"
            s += "    return _" + hash_key + ";\n"
            s += "  }\n"
        if range_key:
            s += "  const char* rangeKey() const {\n"
            s += '    return "' + range_key + '";\n'
            s += "  }\n"
            s += "  const " + table[range_key]["cpp_type"] + " rangeKeyValue() const {\n"
            s += "    return _" + range_key + ";\n"
            s += "  }\n"

        s += "\n  // notify changed via EventDispatcher\n"
        s += "#if 0\n"
        s += "  void notifyChanged() {\n"
        s += '    auto e = cocos2d::EventCustom("' + snake_case(table_name) + '_changed");\n'
        s += "    e.setUserData(this);\n"
        s += "    cocos2d::Director::getInstance()->getEventDispatcher()->dispatchEvent(&e);\n"
        s += "  }\n"
        s += "#endif\n"

        if with_json:
            s += "\n  // getter via json\n"
            s += "  json_t* toJson() {\n"
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
                        s += "      json_array_append(a_" + item_name + ", (*it)->toJson());\n"
                    s += "    }\n"
                    s += '    json_object_set(json, "' + item_name + '", a_' + item_name + ');\n'
                elif item_type == 'string':
                    s += '    json_object_set(json, "' + item_name + '", json_string(_' + item_name + '.c_str()));\n'
                elif item_type in ('int', 'long'):
                    s += '    json_object_set(json, "' + item_name + '", json_integer(_' + item_name + '));\n'
                elif item_type in ('float', 'double'):
                    s += '    json_object_set(json, "' + item_name + '", json_real(_' + item_name + '));\n'
                elif item_type in ('bool'):
                    s += '    json_object_set(json, "' + item_name + '", json_boolean(_' + item_name + '));\n'
                else:
                    s += '    json_object_set(json, "' + item_name + '", _' + item_name + '->toJson());\n'
            s += "    return json;\n";
            s += "  }\n"

            s += "\n  // setter via json\n"
            s += "  void fromJson(json_t* json) {\n"
            if has_vector:
                s += "    int i;\n"
                s += "    json_t* v;\n"
            for item_name, item in table.iteritems():
                item_type = item["item_type"]
                if item["is_vector"]:
                    s += "    _" + item_name + ".clear();\n"
                    s += '    json_array_foreach(json_object_get(json, "' + item_name + '")' + ", i, v) {\n"
                    if item_type in ('string'):
                        s += "      _" + item_name + ".push_back(json_string_value(v));\n"
                    elif item_type in ('int', 'long'):
                        s += "      _" + item_name + ".push_back(json_integer_value(v));\n"
                    elif item_type in ('float', 'double'):
                        s += "      _" + item_name + ".push_back(json_real_value(v));\n"
                    elif item_type in ('bool'):
                        s += "      _" + item_name + ".push_back(json_boolean_value(v));\n"
                    else:
                        s += "      _" + item_name + ".push_back(" + item["cpp_type"] + "(new " + item["item_type"] + "(v)));\n"
                    s += "    }\n"
                elif item_type in ('string'):
                    s += "    _" + item_name + ' = json_string_value(json_object_get(json, "' + item_name + '"));\n'
                elif item_type in ('int', 'long'):
                    s += "    _" + item_name + ' = json_integer_value(json_object_get(json, "' + item_name + '"));\n'
                elif item_type in ('float', 'double'):
                    s += "    _" + item_name + ' = json_real_value(json_object_get(json, "' + item_name + '"));\n'
                elif item_type in ('bool'):
                    s += "    _" + item_name + ' = json_boolean_value(json_object_get(json, "' + item_name + '"));\n'
                else:
                    s += "    _" + item_name + '->fromJson(json_object_get(json, "' + item_name + '"));\n'
            s += "  }\n"
            s += "  // construct with json\n"
            s += "  " + table_name + "(json_t* json) {\n"
            s += "    fromJson(json);\n"
            s += "  }\n"

        if with_msgpack:
            s += "\n  // setter via msgpack\n"
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

            s += "\n  // getter via msgpack\n"
            s += "  void fromMsgpack(msgpack::object& obj) {\n"
            s += "    std::map<std::string, msgpack::object> __map = obj.as<std::map<std::string, msgpack::object> >();\n"
            for item_name, item in table.iteritems():
                if item["is_vector"]:
                    s += "    _" + item_name + ".clear();\n"
                    s += '    auto __' + item_name + ' = __map.find("' + item_name + '")->second.as<msgpack::object>();\n';
                    s += '    for (msgpack::object* p(__' + item_name + '.via.array.ptr), * const pend(__' + item_name + '.via.array.ptr + __' + item_name + '.via.array.size); p < pend; ++p) {\n'
                    if item["is_default_type"]:
                        s += '      _' + item_name + '.push_back(p->as<' + item["cpp_type"] + '>());\n'
                    else:
                        s += '      _' + item_name + '.push_back(' + item["cpp_type"] + '(new ' + item["item_type"] + '(*p)));\n'
                    s += '    }\n'
                elif item["is_default_type"]:
                    s += '    _' + item_name + ' =  __map.find("' + item_name + '")->second.as<' + item["cpp_type"] + ' >();\n'
                else:
                    s += '    _' + item_name + '->fromMsgpack(__map.find("' + item_name + '")->second);\n'
            s += "  }\n"
            s += "  // construct with json\n"
            s += "  " + table_name + "(msgpack::object& obj) {\n"
            s += "    fromMsgpack(obj);\n"
            s += "  }\n"

        if with_json and fbs_root_type == table_name:
            s += "\n  // top level of JSON IO\n"
            s += "  json_t* serializeJson(std::string& target) {\n"
            for item_name, item in table.iteritems():
                s += '    if (target == "' + item_name + '") {\n'
                if item["is_vector"]:
                    s += '      auto a_' + item_name + ' = json_array();\n'
                    s += '      for (auto it = _' + item_name + '.begin(); it != _' + item_name + '.end(); it++) {\n'
                    s += '        json_array_append(a_' + item_name + ', (*it)->toJson());\n'
                    s += '      }\n'
                    s += '      return a_' + item_name +';\n'
                else:
                    s += '      return _' + item_name + '->toJson();\n'
                s += '    }\n'
            s += "    return json_null();\n"
            s += "  }\n"
            s += "  void deserializeJson(json_t* json, std::string& target) {\n"
            if has_vector:
                s += "    int i;\n"
                s += "    json_t* v;\n"
            for item_name, item in table.iteritems():
                s += '    if (target == "' + item_name + '") {\n'
                if item["is_vector"]:
                    s += "      _" + item_name + ".clear();\n"
                    s += "      json_array_foreach(json, i, v) {\n"
                    s += "        auto __" + item_name + " = std::make_shared<" + item["item_type"] + ">();\n"
                    s += "        __" + item_name + "->fromJson(v);\n"
                    s += "        _" + item_name + ".push_back(__" + item_name + ");\n"
                    s += '      }\n'
                else:
                    s += '      _' + item_name + '->fromJson(json);\n'
                s += '      return;\n'
                s += '    }\n'
            s += "  }\n"

        if with_msgpack and fbs_root_type == table_name:
            s += "\n  // top level of msgpack IO\n"
            s += "  void serializeMsgpack(msgpack::packer<msgpack::sbuffer>& pk, std::string& target) {\n"
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
            s += "  void deserializeMsgpack(msgpack::object& obj, std::string& target) {\n"
            for item_name, item in table.iteritems():
                s += '    if (target == "' + item_name + '") {\n'
                if item["is_vector"]:
                    s += '      for (msgpack::object* p(obj.via.array.ptr), * const pend(obj.via.array.ptr + obj.via.array.size); p < pend; ++p) {\n'
                    s += '        auto __' + item_name + ' = std::make_shared<' + item["item_type"] + '>();\n'
                    s += '        __' + item_name + '->fromMsgpack(*p);\n'
                    s += '        _' + item_name + '.push_back(__' + item_name +');\n'
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
                    s += "    std::vector<" + item["cpp_type"] + " v_" + item_name + ";\n"
                    s += "    for (auto it = _" + item_name + ".begin(); it != _" + item_name + ".end(); it++) {\n"
                    if item["item_type"] == 'string':
                        s += "      v_" + item_name + "->push_back(fbb->CreateString(*it));\n"
                    elif item["is_default_type"]:
                        s += "      v_" + item_name + "->push_back(*it);\n"
                    else:
                        s += "      v_" + item_name + "->push_back((*it)->to_flatbuffers(fbb));\n"
                    s += "    }\n"
                    s += "    auto fb_" + item_name + " = fbb->CreateVector(v_" + item_name + ");\n"
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
        s += "};\n\n" # end of class

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

    with open(dst, 'w') as f:
        f.write(s)

# ---
# main function
#
if __name__ == '__main__':
    logging.basicConfig(level = logging.INFO, format = '%(asctime)-15s %(levelname)s %(message)s')

    parser = argparse.ArgumentParser(description = 'convert fbs schema to C++ classes')
    parser.add_argument('input_fbs',     metavar = 'input.fbs',  help = 'input FlatBuffers schema file')
    parser.add_argument('output_class',  metavar = 'output.h',   help = 'output class file (C++ header)')
    parser.add_argument('--namespace',   help = 'name space override')
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
    fbs2class(args.input_fbs, args.output_class, args.namespace, args.json, args.msgpack, args.fbs)
    exit(0)


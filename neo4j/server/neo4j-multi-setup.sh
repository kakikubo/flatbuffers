#!/bin/sh

user_name=$1
port=$2
if [ -z "$user_name" -o -z "$port" ]; then
  echo "Usage: $0 <user.name> <port>"
  exit 1
fi
NEO4J_ROOT=`find /usr/local/Cellar/neo4j/ -name libexec -type d`
NEO4J_HOME=${NEO4J_MULTI_ROOT:-~/neo4j}/$user_name
NEO4J_PORT=$port

template_dir=`dirname $0`/conf
template_bin=`dirname $0`/../../script/template.py
env_template_json=`dirname $0`/env.template.json

# directory
for dir in data/log conf; do
  mkdir -p $NEO4J_HOME/$dir || exit $?
done

# symlink
for dir in bin lib system; do
  rm -f $NEO4J_HOME/$dir
  ln -s $NEO4J_ROOT/$dir $NEO4J_HOME/$dir || exit $?
done

# environment configuration file
env_json=$NEO4J_HOME/neo4j_env.json
$template_bin $env_template_json "{\"NEO4J_HOME\": \"$NEO4J_HOME\", \"NEO4J_ROOT\": \"$NEO4J_ROOT\", \"port\": $NEO4J_PORT}" > $env_json

# neo4j conf
for file in $template_dir/*; do
  $template_bin $file $env_json > $NEO4J_HOME/conf/`basename $file` || exit $?
done

exit 0

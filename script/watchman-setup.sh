#!/bin/sh

watchman=/usr/local/bin/watchman
jq=/usr/loca/bin/jq

cd `dirname $0`/..
script_dir=`pwd`

root_dir=$1
[ -n "$root_dir" ] || root_dir=$script_dir
cd $root_dir || exit $?
root_dir=`pwd`
echo "watch root dir: $root_dir"

for template in $script_dir/hook/*.json.template; do
  json=`echo $template | sed -e 's/\.template$//'`
  cat $template | sed -e "s!__ROOT_DIR__!$root_dir!g" | sed -e "s!__SCRIPT_DIR__!$script_dir!g" > $json
  path=`cat $json | jq -r '.[1]'`
  name=`cat $json | jq -r '.[2]["name"]'`

  [ -d $path ] || mkdir -p $path || exit $?

  echo "delete trigger (for update): $path $name"
  $watchman trigger-del $path $name

  echo "set trigger: $json"
  $watchman trigger -j < $json || exit $?
done

exit 0

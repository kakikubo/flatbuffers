#!/bin/sh

watchman=/usr/local/bin/watchman
jq=/usr/loca/bin/jq

cd `dirname $0`/..
tool_dir=`pwd`

root_dir=$1
[ -n "$root_dir" ] || root_dir=$tool_dir/../kms_master_asset
cd $root_dir || exit $?
root_dir=`pwd`
echo "watch root dir: $root_dir"

base=`basename "$root_dir"`
# setup dirs
# TODO webview
dirs="master user contents/files contents/master editor/areaInfo editor_schema area ui lua shader glyph_designer manifests/dev"
for dir in $dirs; do
  echo "setup $root_dir/$dir"
  mkdir -p $root_dir/$dir || exit $?
done

# setup watchman trigger
for template in $tool_dir/watchman/template/*.json.template; do
  json=`echo $template | sed -e 's/\.template$//'`
  cat $template | sed -e "s!__ROOT_DIR__!$root_dir!g" | sed -e "s!__TOOL_DIR__!$tool_dir!g" > $json
  path=`cat $json | jq -r '.[1]'`
  name=`cat $json | jq -r '.[2]["name"]'`

  [ -d $path ] || mkdir -p $path || exit $?

  echo "delete trigger (for update): $path $name"
  $watchman trigger-del $path $name

  echo "set trigger: $json"
  $watchman trigger -j < $json || exit $?
done

exit 0

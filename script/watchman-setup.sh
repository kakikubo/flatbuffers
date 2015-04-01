#!/bin/sh

watchman=/usr/local/bin/watchman
name=asset

cd `dirname $0`/../
root_dir=`pwd`
watch_dir=$root_dir/bundled/preload/files

template=$root_dir/hook/watchman.json.template
json=$root_dir/hook/watchman.json
cat $template | sed -e "s!__ROOT_DIR__!$root_dir!g" > $json

cd $root_dir
$watchman watch $watch_dir || exit $?
$watchman trigger-del $watch_dir $name
$watchman trigger -j < $json

exit 0

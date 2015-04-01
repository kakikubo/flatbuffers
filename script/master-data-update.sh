#!/bin/sh

master=$1
[ -n "$master" ] || master=master

#api_url=http://10.1.1.24/game_client/master_data/$master
#api_url=http://10.1.1.24/asset/$master/master_data.json
api_url=http://tmp-kiyoto-suzuki-ffl.gree-dev.net/asset/$master/master_data.json
master_data_root=bundled/preload/files
web_asset_root=/var/www/asset/$master/

curl $api_url > $file.tmp
ret=$?
if [ $ret -eq 0 ]; then
  mv $file.tmp $master_data_root/master_data.json
fi

if [ -d $web_asset_root ]; then
  rsync -a $web_asset_root $master_data_root
fi
git status
exit $ret

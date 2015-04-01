#!/bin/sh

source `dirname $0`/box-config.sh
box_access_token=`git config box.accesstoken`
box_refresh_token=`git config box.refreshtoken`
if [ -z "$box_access_token" -o -z "$box_refresh_token" ]; then
  echo "box.accesstoken or box.refreshtoken are not found: please authenticate box at first."
  exit 1
fi

res=`curl $box_oauth_url/token --silent -X POST -d "grant_type=refresh_token&refresh_token=$box_refresh_token&client_id=$box_client_id&client_secret=$box_client_secret"`
ret=$?
if [ $ret -ne 0 ]; then
  echo "failed to get box access token ($ret): $res"
  exit 1
fi
error=`echo $res | jq -r '.error'`
error_description=`echo $res | jq -r '.error_description'`
if [ "$error" != "null" ]; then
  echo "failed to get box access token ($error): $error_description"
  exit 1
fi

box_access_token=`echo $res | jq -r '.access_token'`
box_refresh_token=`echo $res | jq -r '.refresh_token'`
box_expires_in=`echo $res | jq -r '.expires_in'`
git config box.accesstoken $box_access_token || exit $?
git config box.refreshtoken $box_refresh_token || exit $?

# test to access (for debug)
#curl $box_api_url/folders/0 -H "Authorization: Bearer $box_access_token" | jq '.'

echo "box access token is refreshed successfully: expires in $box_expires_in"
echo "access token: $box_access_token"
echo "refresh token: $box_refresh_token"
exit 0

#!/bin/sh

box_token_url=https://app.box.com/api/oauth2/token
box_api_url=https://www.box.com/api/2.0
box_client_id=`git config git-media.boxclientid`
box_client_secret=`git config git-media.boxclientsecret`
box_access_token=`git config git-media.boxaccesstoken`
box_refresh_token=`git config git-media.boxrefreshtoken`
if [ -z "$box_client_id" -o -z "$box_client_secret" ]; then
  echo "git-media.boxclientid or git-media.boxclientsecret are not found: do you setup git-media on box?"
  exit 1
fi
if [ -z "$box_access_token" -o -z "$box_refresh_token" ]; then
  echo "git-media.boxaccesstoken or git-media.boxrefreshtoken are not found: please authenticate box at first."
  exit 1
fi

res=`curl $box_token_url --silent -X POST -d "grant_type=refresh_token&refresh_token=$box_refresh_token&client_id=$box_client_id&client_secret=$box_client_secret"`
ret=$?
if [ $ret -ne 0 ]; then
  echo "failed to get box access token ($ret): $res"
  exit 1
fi

box_access_token=`echo $res | jq -r '.access_token'`
box_refresh_token=`echo $res | jq -r '.refresh_token'`
box_expires_in=`echo $res | jq -r '.expires_in'`
git config git-media.boxaccesstoken $box_access_token || exit $?
git config git-media.boxrefreshtoken $box_refresh_token || exit $?

# test to access (for debug)
#curl $box_api_url/folders/0 -H "Authorization: Bearer $box_access_token" | jq '.'

echo "box access token is refreshed successfully: expires in $box_expires_in"
echo "access token: $box_access_token"
echo "refresh token: $box_refresh_token"
exit 0

#!/bin/sh

source `dirname $0`/box-config.sh

echo "-- please sign-on with box oauth2 on your browser."
echo "use 'single-sign-on (SSO)' by xxx@gree.net."
echo "authenticate and get 'Box Code' like 'QINfVCdKFga6zjOm6XEoRZ2QeDPcWrmL'."
echo "input Box Code: "
open "$box_oauth_url/authorize?response_type=code&state=$box_redirect_uri&client_id=$box_client_id"
read box_code

res=`curl $box_oauth_url/token --silent -X POST -d "grant_type=authorization_code&client_id=$box_client_id&client_secret=$box_client_secret&code=$box_code"`
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

echo "box authentication is completed successfully: expires in $box_expires_in"
echo "access token: $box_access_token"
echo "refresh token: $box_refresh_token"
exit 0

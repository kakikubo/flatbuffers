#!/bin/sh

box_oauth2_url=https://app.box.com/api/oauth2/authorize?response_type=code
box_client_id=tmfiqodo0t15ln6tns6nuw1m6so4izre
box_client_secret=ATGmDrTo1qly4Os4HJQF9zNs95qlrK0C
box_redirect_uri=https://refactoring.gree-dev.net/box
box_folder_id=3225268882
howto_url=https://confluence.gree-office.net/display/~masaki.fujimoto/20150225-git-media-with-box

echo "-- check git-media with box installed."
git_media=`which git-media`
if [ $? -ne 0 ]; then
  echo "git-media with box is not installed."
  echo "please build and install it by..."
  echo "  \$ cd ~"
  echo "  \$ git clone git@github.com:fujimoto/git-media.git"
  echo "  \$ cd git-media"
  echo "  \$ sudo gem install bundler"
  echo "  \$ bundle install"
  echo "  \$ gem build git-media.gemspec"
  echo "  \$ sudo gem build git-media-*.gem"
  echo "see also $howto_url"
  exit 1
fi

echo "-- set git config filter.media."
git config filter.media.clean "git-media filter-clean" || exit $?
git config filter.media.smudge "git-media filter-smudge" || exit $?

git config git-media.transport box || exit $?
git config git-media.autodownload true || exit $?
git config git-media.boxclientid $box_client_id || exit $?
git config git-media.boxclientsecret $box_client_secret || exit $?
git config git-media.boxredirecturi $box_redirect_uri || exit $?
git config git-media.boxfolderid $box_folder_id || exit $?

echo "-- please sign-on with box oauth2 on your browser."
echo "use 'single-sign-on (SSO)' by xxx@gree.net."
echo "authenticate and get 'Box Code' like 'QINfVCdKFga6zjOm6XEoRZ2QeDPcWrmL'."
open "https://app.box.com/api/oauth2/authorize?response_type=code&state=$box_redirect_uri&client_id=$box_client_id"

echo "-- please set 'Box Code'."
git media status || exit $?

echo "-- git media sync..."
git status || exit $?
git media sync || exit $?
exit 0

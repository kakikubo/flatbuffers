#!/bin/sh

cd `dirname $0`

# fixed path
for i in ~/box/kms_*_asset; do
  ./watchman-setup.sh $i || exit $?
done

exit 0

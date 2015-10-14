#!/bin/sh

MERGEPBX_TARGET=mergepbx
MERGEPBX_PREFIX=/usr/local/bin
MERGEPBX_BUILD_DIR=/tmp
MERGEPBX_REPO=https://github.com/simonwagner/mergepbx.git

build()
{
  cd $MERGEPBX_BUILD_DIR/$MERGEPBX_TARGET
  ./build.py
}

# make sure that mergepbx exists
mergepbx=`which $MERGEPBX_TARGET 2>&1`
ret=$?
if [ $ret -eq 0 ] && [ -x "$mergepbx" ]; then
  echo "The mergepbx has already been installed."
  exit 0
fi

echo "Installing..."

rm -rf $MERGEPBX_BUILD_DIR/$MERGEPBX_TARGET 1>/dev/null 2>&1
git clone $MERGEPBX_REPO $MERGEPBX_BUILD_DIR/$MERGEPBX_TARGET 1>/dev/null 2>&1
if [ $? -ne 0 ]; then
  echo "Error: Check the url of the mergepbx repository or the destination path."
  echo "URL: ${MERGEPBX_REPO}"
  echo "Destination: ${MERGEPBX_BUILD_DIR}/${MERGEPBX_TARGET}"
  exit $?
fi

build 1> /dev/null
if [ $? -ne 0 ]; then
  exit $?
fi

cp $MERGEPBX_BUILD_DIR/$MERGEPBX_TARGET/$MERGEPBX_TARGET $MERGEPBX_PREFIX 1> /dev/null 2>&1
if [ $? -ne 0 ]; then
  echo "Something goes wrong to copy the mergepbx."
  echo "Using sudo to run commands as root."
  exit $?
fi

git config --global merge.mergepbx.name "Xcode project files merger"
git config --global merge.mergepbx.driver "mergepbx %O %A %B"

echo "

Added configurations into the global .gitconfig file.

[merge \"mergepbx\"]
    name = Xcode project files merger
    driver = mergepbx %O %A %B


# Configure your repository to use the driver

In your repository root directory, open the file .gitattributes (create if it does not exist). Add the following lines to it:

*.pbxproj merge=mergepbx
"

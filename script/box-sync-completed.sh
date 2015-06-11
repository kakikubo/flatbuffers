#!/bin/sh
cd ${HOME:=/Users/kms.jenkins}/Library/Logs/Box/Box\ Sync
ls -tr1 Box\ Sync*.log | tail -1 | tr -d '\n' | xargs -0 grep 'INFO    BoxFSEventMonitor    sync_app_status' | tail -1 | grep -q 'Sync app status is now COMPLETE'
exit $?

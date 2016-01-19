#!/bin/sh
cd ${HOME:=/Users/jenkins}/Library/Logs/Box/Box\ Sync
ls -tr1 Box\ Sync*.log | tail -1 | tr -d '\n' | xargs -0 tail -20000 | grep 'INFO.*FSEventMonitor.*sync_app_status' | tail -1 | grep -q 'Sync app status is now COMPLETE'
exit $?

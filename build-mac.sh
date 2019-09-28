#!/bin/bash

set -e

pyinstaller --windowed Caribou.spec

mkdir -p dist/dmg
cp -r dist/Caribou.app dist/dmg
hdiutil create -volname Caribou -srcfolder dist/dmg -ov -format UDZO Caribou.dmg

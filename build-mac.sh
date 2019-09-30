#!/bin/bash

set -e

pyinstaller --windowed Caribou.spec

mkdir -p dist/dmg
ln -fs /Applications dist/dmg
rm -rf dist/dmg/Caribou.app
cp -r dist/Caribou.app dist/dmg
rm -rf Caribou.dmg
hdiutil create -volname Caribou -srcfolder dist/dmg -ov -format UDZO Caribou.dmg

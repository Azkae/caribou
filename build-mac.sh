#!/bin/bash

if [ $# -ne 1 ]; then
    echo "Missing version"
    echo "Usage: $0 <version>"
    exit
fi

set -e

dmg_name="Caribou_v$1.dmg"

rm -rf dist/Caribou.app
rm -rf dist/Caribou

pyinstaller --windowed Caribou.spec

mkdir -p dist/dmg
ln -fs /Applications dist/dmg
rm -rf dist/dmg/Caribou.app
cp -r dist/Caribou.app dist/dmg
rm -rf $dmg_name
hdiutil create -volname Caribou -srcfolder dist/dmg -ov -format UDZO $dmg_name

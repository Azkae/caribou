#!/bin/bash

set -e

version=$(python -c "import caribou; print(caribou.__version__)")

echo "Building caribou version $version"

dmg_name="Caribou_v$version.dmg"

rm -rf dist/Caribou.app
rm -rf dist/Caribou

pyinstaller --clean --windowed Caribou.spec

mkdir -p dist/dmg
ln -fs /Applications dist/dmg
rm -rf dist/dmg/Caribou.app
cp -r dist/Caribou.app dist/dmg
rm -rf $dmg_name
hdiutil create -volname Caribou -srcfolder dist/dmg -ov -format UDZO $dmg_name

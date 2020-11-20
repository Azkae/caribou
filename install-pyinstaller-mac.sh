#!/bin/bash

git clone https://github.com/pyinstaller/pyinstaller.git build/pyinstaller
cd build/pyinstaller
git checkout develop
cd bootloader
export MACOSX_DEPLOYMENT_TARGET=10.13
export CFLAGS=-mmacosx-version-min=10.13
export CPPFLAGS=-mmacosx-version-min=10.13
export LDFLAGS=-mmacosx-version-min=10.13
export LINKFLAGS=-mmacosx-version-min=10.13
python ./waf all
cd ..
pip install .
cd ../..

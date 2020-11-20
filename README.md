# Caribou

Create your own REST client GUI with a few line of code: 
see `ex.py` for a configuration example.

```
pip3 install -e .
caribou ex.py
```

Inspired by `click` and `requests`.

Todos:

- check for route / group duplicates
- fix request preview for Content-Type other than json
- add open in editor button
- add the ability to edit the raw preview
- add color for get & post in readme
- add a list type? (which widget?)

## Mac setup

Pyenv install:

```
MACOSX_DEPLOYMENT_TARGET=10.13 PYTHON_CONFIGURE_OPTS=--enable-shared pyenv install 3.9.0
```


Install:
```
./install-pyinstaller-mac.sh
pip install -e .
```

Build:
```
./build-mac.sh
```

from setuptools import setup

setup(
    name='caribou',
    version='0.1',
    install_requires=[
        'pyside2',
    ],
    entry_points='''
        [console_scripts]
        caribou=caribou.cli:main
    ''',
)

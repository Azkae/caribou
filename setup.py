from setuptools import setup
# from cx_Freeze import setup, Executable

setup(
    name='caribou',
    version='0.1',
    install_requires=[
        'pyside2',
        'Pygments',
    ],
    entry_points='''
        [console_scripts]
        caribou=caribou.cli:main
    ''',
    # executables=[
    #     Executable('caribou/cli.py')
    # ]
)

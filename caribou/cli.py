import sys
from caribou.ui import run


def main():
    if len(sys.argv) != 2:
        print('Usage: caribou <file.py>')
        exit(1)
    run(sys.argv[1])


if __name__ == '__main__':
    main()

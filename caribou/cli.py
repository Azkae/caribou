import sys
from caribou.ui import run


def main():
    if len(sys.argv) < 2:
        path = None
    else:
        path = sys.argv[1]
    run(path)


if __name__ == '__main__':
    main()

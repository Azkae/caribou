import sys
from caribou.ui import run


def main():
    if len(sys.argv) != 2:
        print('Usage: caribou <file.py>')
        path = '/Users/ouabde_r/signals/server/docs/routes.py'
        # exit(1)
    else:
        path = sys.argv[1]
    run(path)


if __name__ == '__main__':
    main()

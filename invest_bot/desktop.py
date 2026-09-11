"""Windows executable entry point for the dashboard."""

import argparse

from invest_bot.dashboard import serve


def main(argv=None):
    parser = argparse.ArgumentParser(description='차곡 투자 대시보드')
    parser.add_argument('--port', type=int, default=8765)
    parser.add_argument('--no-browser', action='store_true', help='브라우저를 자동으로 열지 않습니다.')
    args = parser.parse_args(argv)
    serve(port=args.port, open_browser=not args.no_browser)


if __name__ == '__main__':
    main()

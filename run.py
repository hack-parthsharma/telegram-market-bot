#!/usr/bin/env python3
"""Entry point. Usage: python run.py {premarket|postclose|news|test}"""
import sys


def main():
    job = sys.argv[1] if len(sys.argv) > 1 else "postclose"

    if job == "news":
        from src import news
        news.run()
    elif job == "premarket":
        from src import digest
        digest.pre_market()
    elif job == "postclose":
        from src import digest
        digest.post_close()
    elif job == "test":
        # Send a one-off analysis to verify secrets/data/AI all work.
        from src import digest
        symbol = sys.argv[2] if len(sys.argv) > 2 else "RELIANCE.NS"
        tf = sys.argv[3] if len(sys.argv) > 3 else "daily"
        digest._analyze_symbol(symbol, tf)
    else:
        sys.exit(f"Unknown job '{job}'. Use: premarket | postclose | news | test")


if __name__ == "__main__":
    main()

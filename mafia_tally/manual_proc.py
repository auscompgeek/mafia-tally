#!/usr/bin/env python3

import json
import sys

from mafia_tally import app, cache
from mafia_tally.tally import create_vote_tally, make_html_tally, textify_tally


def main():
    comments = json.load(sys.stdin)
    tally = create_vote_tally()

    with app.app_context():
        page = make_html_tally(tally, comments)
    text = textify_tally(tally)
    print(text)
    cache.write_day_text(text)
    cache.write_day_html(page)


if __name__ == "__main__":
    main()

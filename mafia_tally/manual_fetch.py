#!/usr/bin/env python3

import json
import pprint
import readline  # noqa
import sys

from mafia_tally import config
from mafia_tally.fetcher import fetch_comments


def print_player_list():
    for i, player in enumerate(sorted(config.players)):
        print(i, player, sep='. ', file=sys.stderr)


def input_player() -> str:
    players = sorted(config.players)

    print('Pick a player: ', file=sys.stderr, end='')
    inp = input()
    while inp == '?':
        print_player_list()
        print('Pick a player: ', file=sys.stderr, end='')
        inp = input()

    if inp.isdigit():
        return players[int(inp)]

    return inp


def main():
    print_player_list()
    comments = fetch_comments()

    for i, comment in enumerate(comments):
        if 'from' not in comment:
            print('Comment', i, file=sys.stderr)
            pprint.pprint(comment, stream=sys.stderr)
            player = input_player()
            comment['from'] = {'name': player}
            print(file=sys.stderr)

    json.dump(comments, sys.stdout)


if __name__ == "__main__":
    main()

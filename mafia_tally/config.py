import json
import os
from typing import Dict, Set

import werkzeug.security

config_dir = os.path.join(os.path.dirname(__file__), '..', 'config')
get_path = lambda filename: os.path.join(config_dir, filename)
day_config_file = get_path('day.json')
access_token_file = get_path('access_token.txt')
players_file = get_path('players.txt')
admin_passhash_file = get_path('passhash.txt')

group_id: int = 328346913872436  # lol let's hardcode this
post_id: int
day_id: int
cutoff: str
players: Set[str]
pics: Dict[str, str]


def get_access_token() -> str:
    with open(access_token_file) as f:
        return f.read().strip()


def get_passhash() -> str:
    with open(admin_passhash_file) as f:
        return f.read().strip()


def check_admin_password(password: str) -> bool:
    return werkzeug.security.check_password_hash(get_passhash(), password)


def load_day_config():
    global post_id
    global day_id
    global cutoff

    with open(day_config_file) as f:
        day_info = json.load(f)

    post_id = day_info['post_id']
    day_id = day_info['day_id']
    cutoff = day_info['cutoff']


def get_players() -> Set[str]:
    with open(players_file) as f:
        return set(map(str.strip, f))


def load_players():
    global players
    players = get_players()


def load_pics():
    global pics
    with open(get_path('pics.json')) as f:
        pics = json.load(f)


def load():
    load_day_config()
    load_players()
    load_pics()


def save_day_config():
    with open(day_config_file, 'w') as f:
        json.dump(
            {'post_id': post_id, 'day_id': day_id, 'cutoff': cutoff}, f, indent='\t'
        )


def save_players():
    with open(players_file, 'w') as f:
        print(*players, sep='\n', file=f)


def save():
    save_day_config()
    save_players()


load()

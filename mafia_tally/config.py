import json
import os

import werkzeug.security


config_dir = os.path.join(os.path.dirname(__file__), '..', 'config')
get_path = lambda filename: os.path.join(config_dir, filename)
day_config_file = get_path('day.json')
access_token_file = get_path('access_token.txt')
players_file = get_path('players.txt')
admin_passhash_file = get_path('passhash.txt')

group_id = 328346913872436  # lol let's hardcode this
post_id = None  # type: int
day_id = None  # type: int
cutoff = None  # type: str
players = None  # type: set


def get_access_token():
    with open(access_token_file) as f:
        return f.read().strip()


def get_passhash():
    with open(admin_passhash_file) as f:
        return f.read().strip()


def check_admin_password(password):
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


def get_players():
    with open(players_file) as f:
        return set(map(str.strip, f))


def load_players():
    global players
    players = get_players()


def load():
    load_day_config()
    load_players()


def save_day_config():
    with open(day_config_file, 'w') as f:
        json.dump({'post_id': post_id, 'day_id': day_id, 'cutoff': cutoff}, f, indent='\t')


def save_players():
    with open(players_file, 'w') as f:
        print(*players, sep='\n', file=f)


def save():
    save_day_config()
    save_players()


load()

import logging

import arrow
from flask import Blueprint, render_template, request

from . import config

bp = Blueprint('admin', __name__, url_prefix='/admin')
logger = logging.getLogger(__name__)


@bp.route('/', methods=['GET', 'POST'])
def admin():
    if request.method == 'GET':
        return render_template('admin.html', config=config)

    if config.check_admin_password(request.form['password']):
        post_id = int(request.form['post_id'])
        day_id = int(request.form['day_id'])
        cutoff = arrow.get(request.form['cutoff']).floor('second')

        config.post_id = post_id
        config.day_id = day_id
        config.cutoff = cutoff.to('utc').isoformat()
        config.save_day_config()

        dead = request.form.getlist('dead')
        if dead:
            for player in dead:
                config.players.remove(player)
            config.save_players()

        return 'Success!'
    else:
        logger.warning('Incorrect password: %s', request.form['password'])
        return 'Incorrect password.'


@bp.route('/reload')
def reload():
    config.load()
    return 'Success!'

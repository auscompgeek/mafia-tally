import arrow
from flask import request, render_template

from .app import app
from . import config
from . import tally


@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if request.method == 'GET':
        return render_template('admin.html', config=config)

    if config.check_admin_password(request.form['password']):
        post_id = int(request.form['post_id'])
        day_id = int(request.form['day_id'])
        cutoff = arrow.get(request.form['cutoff']).floor('second')

        config.post_id = post_id
        config.day_id = day_id
        config.cutoff = cutoff.isoformat()
        config.save_day_config()

        dead = request.form.getlist('dead')
        if dead:
            for player in dead:
                config.players.remove(player)
            config.save_players()

        return 'Success!'
    else:
        app.logger.warning('Incorrect password: %s', request.form['password'])
        return 'Incorrect password.'

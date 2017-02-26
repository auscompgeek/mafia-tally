from io import StringIO

import arrow
from flask import abort, make_response, render_template, url_for
from jinja2 import Markup, escape

from .app import app
from . import cache
from . import config
from .fetcher import fetch_comments, fetch_members
from .tallier import VotesTally, VoteInfo


HTML_HEADER = """\
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8" />
<title>{title} - Mafia Tally</title>
<meta name="viewport" content="width=device-width" />
<link rel="stylesheet" href="{css}" />
</head>
<body>"""

HTML_FOOTER = """
</body>
</html>
"""

TEXT_MIME_TYPE = 'text/plain; charset=utf-8'


html_header = lambda title: HTML_HEADER.format(title=title, css=url_for('static', filename='style.css'))
wrap_page = lambda title, page: html_header(title) + page + HTML_FOOTER


def create_vote_tally():
    return VotesTally(voting=config.players, votables=config.players, cutoff=config.cutoff)


def textify_tally(tally):
    now = arrow.now()
    stringio = StringIO()

    tally.display_votes(file=stringio)
    stringio.write('\n')

    tally.print_abstaining(file=stringio)
    tally.print_unvoted(file=stringio)
    tally.print_did_not_vote(file=stringio)

    print('\nLast updated:', now, file=stringio)

    if now >= arrow.get(config.cutoff):
        if tally.votes:
            lynched = max(tally.votes, key=tally.num_votes.get)
            print(lynched, 'was lynched (probably).', file=stringio)
        else:
            print('Nobody was voted for lynching at the end of the day. Boo.', file=stringio)

    return stringio.getvalue()


@app.route('/text')
def text():
    if cache.day_text_is_stale():
        comments = fetch_comments()
        tally = create_vote_tally()

        for comment in comments:
            tally.parse_comment(comment)

        day_text = textify_tally(tally)
        cache.write_day_text(day_text)
        resp = make_response(day_text)
    else:
        resp = make_response(cache.read_day_text())

    resp.headers['Content-Type'] = TEXT_MIME_TYPE
    return resp


@app.route('/<int:day_id>.txt')
def day_text(day_id):
    try:
        return make_response(cache.read_cache('%d.txt' % day_id), {'Content-Type': TEXT_MIME_TYPE})
    except FileNotFoundError:
        abort(404)


@app.route('/')
def index():
    title = 'Day %d Votes' % config.day_id
    if cache.day_html_is_stale():
        comments = fetch_comments()
        tally = create_vote_tally()
        num_skipped = 0
        comment_details = []

        for comment in comments:
            is_vote, details = tally.parse_comment(comment)
            if is_vote:
                if num_skipped:
                    comment_details.append((None, num_skipped))
                    num_skipped = 0
                comment_details.append((comment, details))
            else:
                num_skipped += 1

        cache.write_day_text(textify_tally(tally))

        votes = sorted(tally.votes.items(), key=lambda x: -tally.num_votes[x[0]])

        # FIXME can we avoid this dance?
        pictures = {member['name']: member['picture']['data']['url'] for member in fetch_members()}

        page = render_template(
            'tally.html', now=arrow.now(), tally=tally, votes=votes,
            config=config, comments=comment_details, pictures=pictures,
            VoteInfoType=VoteInfo.Type)
        cache.write_day_html(page)

        return wrap_page(title, page)
    else:
        return wrap_page(title, cache.read_day_html())


@app.route('/<int:day_id>')
def day_page(day_id):
    try:
        return wrap_page('Day %d Votes' % day_id, cache.read_cache('%d.html' % day_id))
    except FileNotFoundError:
        abort(404)


@app.route('/all')
def all_tallies():
    def generate():
        yield header
        for day in range(1, config.day_id + 1):
            try:
                yield cache.read_cache('%d.html' % day)
            except FileNotFoundError:
                pass
        yield HTML_FOOTER

    # Generate header whilst we still have a route context
    header = html_header('All tallies')
    return Response(generate())


@app.template_filter()
def nl2br(value):
    result = '<br />\n'.join([escape(x) for x in value.splitlines()])
    result = Markup(result)
    return result

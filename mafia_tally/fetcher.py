import requests

from . import config
from .app import app


COMMENTS_URI_TEMPLATE = 'https://graph.facebook.com/v2.3/{post_id}/comments?fields=from,message,message_tags,created_time&limit=200&access_token={access_token}'
MEMBERS_URI_TEMPLATE = 'https://graph.facebook.com/v2.2/{group_id}/members?fields=id,name,picture{{url}}&limit=200&access_token={access_token}'

session = requests.Session()


def fetch_comments():
    r = session.get(COMMENTS_URI_TEMPLATE.format(access_token=config.get_access_token(), post_id=config.post_id))
    j = r.json()
    if 'data' in j:
        return j['data']
    app.logger.error('Error from Graph API: %s', j)


def fetch_members():
    r = session.get(MEMBERS_URI_TEMPLATE.format(access_token=config.get_access_token(), group_id=config.group_id))
    j = r.json()
    if 'data' in j:
        return j['data']
    app.logger.error('Error from Graph API: %s', j)

import logging
from typing import List, Optional

import requests

from . import config

logger = logging.getLogger(__name__)


COMMENTS_URI_TEMPLATE = 'https://graph.facebook.com/v2.7/{post_id}/comments?fields=from{{name,picture{{url}}}},message,message_tags,created_time&limit=200&access_token={access_token}'
MEMBERS_URI_TEMPLATE = 'https://graph.facebook.com/v2.2/{group_id}/members?fields=id,name,picture{{url}}&limit=200&access_token={access_token}'

session = requests.Session()


def fetch_comments() -> Optional[List[dict]]:
    r = session.get(
        COMMENTS_URI_TEMPLATE.format(
            access_token=config.get_access_token(), post_id=config.post_id
        )
    )
    j = r.json()
    if 'data' in j:
        return j['data']
    logger.error('Error from Graph API: %s', j)


def fetch_members():
    raise NotImplementedError
    r = session.get(
        MEMBERS_URI_TEMPLATE.format(
            access_token=config.get_access_token(), group_id=config.group_id
        )
    )
    j = r.json()
    if 'data' in j:
        return j['data']
    logger.error('Error from Graph API: %s', j)

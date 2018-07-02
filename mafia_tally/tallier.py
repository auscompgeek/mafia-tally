import collections
import enum
import re

__all__ = ('VotesTally',)

PRINT_VOTES_TEMPLATE = '{0}: {1:>2} ({2})'
ABSTAIN = 'ABSTAIN'

find_vote_re = re.compile(r'\bV(?:OTE|ote):\s+')
find_unvote_re = re.compile(r'\bU(?:NVOTE|nvote):\s+')

find_vote = find_vote_re.search
find_unvote = find_unvote_re.search

str_list = ', '.join


class VoteInfo(object):
    class Type(enum.IntEnum):
        UNKNOWN_VOTEE = 0
        MULTIPLE_POSSIBLE_VOTEE = 1
        DIDNT_UNVOTE = 2
        UNVOTABLE = 3
        HASNT_VOTED = 4
        UNVOTING_OTHER = 5

    __slots__ = ('type', 'votee')

    def __init__(self, t, votee=None):
        self.type = t
        self.votee = votee

    def __repr__(self):
        return 'VoteInfo({}, {!r})'.format(self.type.name, self.votee)


class VotesTally(object):
    def __init__(self, voting, votables, cutoff, weights=None):
        self.votes = collections.OrderedDict()  # type: Dict[str, List[str]]
        self.num_votes = collections.defaultdict(int)  # type: Dict[str, int]
        self.voter_votes = {}  # type: Dict[str, str]
        self.have_voted = set()  # type: Set[str]
        self.abstaining = []  # type: List[str]
        self.voting = voting  # type: AbstractSet[str]
        self.votables = votables  # type: AbstractSet[str]
        self.cutoff = cutoff
        self.vote_weights = weights or {}  # type: Dict[str, int]

    def parse_comment(self, comment):
        voter = comment['from']['name']
        timestamp = comment['created_time']
        message = comment['message']

        if timestamp >= self.cutoff or voter not in self.voting:
            return False, None

        tags = {tag['offset']: tag['name'] for tag in comment.get('message_tags', [])}
        vote_match = find_vote(message)
        unvote_match = find_unvote(message)

        errs = []
        is_vote = False

        if unvote_match:
            unvotee, err = self.get_votee(message, tags, unvote_match.end())
            if err:
                errs.append(err)

            if unvotee:
                ok, err = self.do_unvote(voter, unvotee)
                is_vote = is_vote or ok
                if err:
                    errs.append(err)

        if vote_match:
            votee, err = self.get_votee(message, tags, vote_match.end())
            if err:
                errs.append(err)
            if votee:
                ok, err = self.do_vote(voter, votee)
                is_vote = is_vote or ok
                errs += err

        return is_vote, errs

    def get_votee(self, message, tags, offset):
        if offset in tags:
            return tags[offset], None

        stuff = message[offset:].lower()
        if stuff.startswith('abstain'):
            return ABSTAIN, None

        possible = [name for name in self.votables if stuff.startswith(name.lower())]
        if not possible:
            return None, VoteInfo(VoteInfo.Type.UNKNOWN_VOTEE)

        if len(possible) != 1:
            # This should never happen.
            votee = max(possible, key=len)
            return votee, VoteInfo(VoteInfo.Type.MULTIPLE_POSSIBLE_VOTEE, votee)

        return possible[0], None

    def do_vote(self, voter, votee):
        #votee = real_name_map.get(votee, votee)
        votes = self.votes
        voter_votes = self.voter_votes
        self.have_voted.add(voter)
        err = []

        if voter in voter_votes:
            err.append(VoteInfo(VoteInfo.Type.DIDNT_UNVOTE, voter_votes[voter]))
            self.do_unvote(voter, votee=None)

        if votee == ABSTAIN:
            self.abstain(voter)
            return True, err

        if votee not in self.votables:
            err.append(VoteInfo(VoteInfo.Type.UNVOTABLE, votee))
            return False, err

        if votee not in votes:
            votes[votee] = []
        votes[votee].append(voter)
        self.num_votes[votee] += self.vote_weights.get(voter, 1)
        voter_votes[voter] = votee

        return True, err

    def do_unvote(self, voter, votee):
        voter_votes = self.voter_votes

        if voter not in voter_votes:
            return False, VoteInfo(VoteInfo.Type.HASNT_VOTED)

        current_vote = voter_votes[voter]

        if votee is not None:
            # unvote specified, sanity check
            if current_vote != votee:
                return False, VoteInfo(VoteInfo.Type.UNVOTING_OTHER, current_vote)

        if current_vote == ABSTAIN:
            self.unabstain(voter)
        else:
            del voter_votes[voter]
            votes = self.votes
            voters = votes[current_vote]
            voters.remove(voter)
            if not voters:
                del votes[current_vote]
            self.num_votes[current_vote] -= self.vote_weights.get(voter, 1)

        return True, None

    def unabstain(self, voter):
        voter_votes = self.voter_votes

        assert voter_votes[voter] == ABSTAIN
        del voter_votes[voter]

        self.abstaining.remove(voter)

    def abstain(self, voter):
        self.abstaining.append(voter)
        self.voter_votes[voter] = ABSTAIN

    def get_did_not_vote(self):
        return self.voting - self.have_voted

    def get_no_registered_vote(self):
        return self.have_voted.difference(self.abstaining, self.voter_votes)

    def display_votes(self, templ=PRINT_VOTES_TEMPLATE, **kwargs):
        votes = self.votes
        if not votes:
            print('No votes yet.', **kwargs)
            return

        num_votes = self.num_votes
        len_longest_votee = max(map(len, votes))
        for votee, voters in sorted(votes.items(), key=lambda x: -num_votes[x[0]]):
            print(
                templ.format(
                    votee.rjust(len_longest_votee), num_votes[votee], str_list(voters)
                ),
                **kwargs,
            )

    def print_abstaining(self, **kwargs):
        print('Abstaining:', list_display_count(self.abstaining), **kwargs)

    def print_unvoted(self, **kwargs):
        unvoted = self.get_no_registered_vote()
        if unvoted:
            print('Unvoted:', list_display_count(unvoted), **kwargs)

    def print_did_not_vote(self, **kwargs):
        print(
            "Didn't vote:",
            list_display_count(sorted(self.get_did_not_vote())),
            **kwargs,
        )


def list_display_count(it):
    return '{0} ({1})'.format(len(it), str_list(it))

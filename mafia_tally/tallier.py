import collections
import enum
import re
from typing import AbstractSet, Dict, List, Mapping, Optional, Set, Tuple

__all__ = ('VotesTally',)

PRINT_VOTES_TEMPLATE = '{0}: {1:>2} ({2})'
ABSTAIN = 'ABSTAIN'

find_vote_re = re.compile(r'^V(?:OTE|ote):\s+', re.MULTILINE)
find_unvote_re = re.compile(r'^U(?:NVOTE|nvote):\s+', re.MULTILINE)

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
        UNKNOWN_VOTER = 6

    __slots__ = ('type', 'votee')

    def __init__(self, t: Type, votee: str = None) -> None:
        self.type = t
        self.votee = votee

    def __repr__(self) -> str:
        if self.votee is None:
            return 'VoteInfo({})'.format(self.type.name)
        return 'VoteInfo({}, {!r})'.format(self.type.name, self.votee)


class VotesTally(object):
    votes: Dict[str, List[str]]
    num_votes: Dict[str, int]
    voter_votes: Dict[str, str]
    have_voted: Set[str]
    abstaining: List[str]
    voting: AbstractSet[str]
    votables: AbstractSet[str]
    cutoff: str
    vote_weights: Mapping[str, int]

    def __init__(
        self,
        voting: AbstractSet[str],
        votables: AbstractSet[str],
        cutoff: str,
        weights: Mapping[str, int] = None,
    ) -> None:
        self.votes = collections.OrderedDict()
        self.num_votes = collections.defaultdict(int)
        self.voter_votes = {}
        self.have_voted = set()
        self.abstaining = []
        self.voting = voting
        self.votables = votables
        self.cutoff = cutoff
        self.vote_weights = weights or {}

    def parse_comment(self, comment: dict) -> Tuple[bool, Optional[List[VoteInfo]]]:
        timestamp: str = comment['created_time']
        message: str = comment['message']

        if timestamp >= self.cutoff:
            return False, None

        voter: str = comment.get('from', {}).get('name')
        if voter is not None and voter not in self.voting:
            return False, None

        tags: Mapping[int, str] = {
            tag['offset']: tag['name'] for tag in comment.get('message_tags', [])
        }
        vote_match = find_vote(message)
        unvote_match = find_unvote(message)

        all_errs: List[VoteInfo] = []
        is_vote = False

        if unvote_match:
            unvotee, err = self.get_votee(message, tags, unvote_match.end())
            if err:
                all_errs.append(err)

            if unvotee:
                if voter is not None:
                    ok, err = self.do_unvote(voter, unvotee)
                else:
                    # HACK
                    ok, err = True, VoteInfo(VoteInfo.Type.UNKNOWN_VOTER)
                is_vote = is_vote or ok
                if err:
                    all_errs.append(err)

        if vote_match:
            votee, err = self.get_votee(message, tags, vote_match.end())
            if err:
                all_errs.append(err)
            if votee:
                if voter is not None:
                    ok, errs = self.do_vote(voter, votee)
                else:
                    # HACK
                    ok = True
                    if not all_errs:
                        errs = [VoteInfo(VoteInfo.Type.UNKNOWN_VOTER)]
                    else:
                        errs = []
                is_vote = is_vote or ok
                all_errs += errs

        return is_vote, all_errs

    def get_votee(
        self, message: str, tags: Mapping[int, str], offset: int
    ) -> Tuple[Optional[str], Optional[VoteInfo]]:
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

    def do_vote(self, voter: str, votee: str) -> Tuple[bool, List[VoteInfo]]:
        # votee = real_name_map.get(votee, votee)
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

    def do_unvote(
        self, voter: str, votee: str = None
    ) -> Tuple[bool, Optional[VoteInfo]]:
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

    def unabstain(self, voter: str):
        voter_votes = self.voter_votes

        assert voter_votes[voter] == ABSTAIN
        del voter_votes[voter]

        self.abstaining.remove(voter)

    def abstain(self, voter: str):
        self.abstaining.append(voter)
        self.voter_votes[voter] = ABSTAIN

    def get_did_not_vote(self) -> AbstractSet[str]:
        return self.voting - self.have_voted

    def get_no_registered_vote(self) -> Set[str]:
        return self.have_voted.difference(self.abstaining, self.voter_votes)

    def display_votes(self, templ: str = PRINT_VOTES_TEMPLATE, **kwargs):
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


def list_display_count(it: list) -> str:
    return '{0} ({1})'.format(len(it), str_list(it))

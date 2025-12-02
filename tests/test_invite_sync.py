from app import config as cfg
from app.handlers import invite_missing_users


class FakeClient:
    def __init__(self, members_by_channel=None, bot_users=None):
        base = members_by_channel or {}
        self.members_by_channel = {
            channel: set(members) for channel, members in base.items()
        }
        self.invites = []
        self.bot_users = bot_users or set()

    def conversations_members(self, channel, limit=1000, cursor=None):
        members = list(self.members_by_channel.get(channel, set()))
        return {"members": members, "response_metadata": {"next_cursor": None}}

    def users_info(self, user):
        return {"user": {"deleted": False, "is_bot": user in self.bot_users}}

    def conversations_invite(self, channel, users):
        self.invites.append((channel, users))
        self.members_by_channel.setdefault(channel, set()).add(users)
        return {"ok": True}


def test_invite_missing_users_simple():
    import app.handlers as handlers

    cfg.check_channels = ["C1"]
    cfg.invite_channels = ["C2"]
    handlers.check_channels = cfg.check_channels
    handlers.invite_channels = cfg.invite_channels
    client = FakeClient(members_by_channel={"C1": ["U1", "U2"], "C2": ["U2"]})
    invite_missing_users(client)
    assert ("C2", "U1") in client.invites


def test_invite_skips_bots():
    import app.handlers as handlers

    cfg.check_channels = ["C1"]
    cfg.invite_channels = ["C2"]
    handlers.check_channels = cfg.check_channels
    handlers.invite_channels = cfg.invite_channels
    client = FakeClient(members_by_channel={"C1": ["U1"], "C2": []}, bot_users={"U1"})
    invite_missing_users(client)
    assert ("C2", "U1") not in client.invites


def test_invite_user_on_join():
    import app.handlers as handlers

    client = FakeClient(members_by_channel={"C1": ["U1"], "C2": ["U2"]})
    handlers.check_channels = ["C1"]
    handlers.invite_channels = ["C2"]
    handlers.invite_user_to_channels(client, "U1", src_channel="C1")
    assert ("C2", "U1") in client.invites


def test_invite_missing_users_idempotent():
    import app.handlers as handlers

    cfg.check_channels = ["C1"]
    cfg.invite_channels = ["C2"]
    handlers.check_channels = cfg.check_channels
    handlers.invite_channels = cfg.invite_channels
    client = FakeClient(members_by_channel={"C1": ["U1"], "C2": []})
    invite_missing_users(client)
    invite_missing_users(client)
    assert len([x for x in client.invites if x == ("C2", "U1")]) == 1

from pathlib import Path

from app import config as cfg
from app.handlers import invite_missing_users


class FakeClient:
    def __init__(self, members_by_channel=None, bot_users=None):
        self.members_by_channel = members_by_channel or {}
        self.invites = []
        self.bot_users = bot_users or set()

    def conversations_members(self, channel, limit=1000, cursor=None):
        members = list(self.members_by_channel.get(channel, []))
        return {"members": members, "response_metadata": {"next_cursor": None}}

    def users_info(self, user):
        return {"user": {"deleted": False, "is_bot": user in self.bot_users}}

    def conversations_invite(self, channel, users):
        self.invites.append((channel, users))
        return {"ok": True}


def test_invite_missing_users_simple():
    cfg.check_channels = ["C1"]
    cfg.invite_channels = ["C2"]
    client = FakeClient(members_by_channel={"C1": ["U1", "U2"], "C2": ["U2"]})
    # Reset invited cache before running
    import app.handlers as handlers

    handlers._already_invited = set()
    invite_missing_users(client)
    assert ("C2", "U1") in client.invites


def test_invite_skips_bots():
    cfg.check_channels = ["C1"]
    cfg.invite_channels = ["C2"]
    client = FakeClient(members_by_channel={"C1": ["U1"], "C2": []}, bot_users={"U1"})
    import app.handlers as handlers

    handlers._already_invited = set()
    invite_missing_users(client)
    assert ("C2", "U1") not in client.invites


def test_invite_user_on_join():
    import app.handlers as handlers

    client = FakeClient(members_by_channel={"C1": ["U1"], "C2": ["U2"]})
    handlers.check_channels = ["C1"]
    handlers.invite_channels = ["C2"]
    handlers._already_invited = set()
    handlers.invite_user_to_channels(client, "U1", src_channel="C1")
    assert ("C2", "U1") in client.invites


def test_invite_missing_users_idempotent():
    import app.handlers as handlers

    handlers._already_invited = set()
    cfg.check_channels = ["C1"]
    cfg.invite_channels = ["C2"]
    client = FakeClient(members_by_channel={"C1": ["U1"], "C2": []})
    invite_missing_users(client)
    invite_missing_users(client)
    # Ensure the invite occurred only once
    assert len([x for x in client.invites if x == ("C2", "U1")]) == 1


def test_invite_cache_persistence(tmp_path):
    import app.config as cfg
    import app.handlers as handlers

    # write cache to a temp path for the test
    cfg.INVITE_CACHE_PATH = str(tmp_path / "invite_cache.json")
    handlers._already_invited = set()
    cfg.check_channels = ["C1"]
    cfg.invite_channels = ["C2"]
    client = FakeClient(members_by_channel={"C1": ["U1"], "C2": []})
    # this should add and persist the invite
    invite_missing_users(client)
    cache_file = Path(cfg.INVITE_CACHE_PATH)
    assert cache_file.exists()
    # ensure permissions are user-only (owner rw)
    perm = cache_file.stat().st_mode & 0o777
    assert perm & 0o600 == 0o600
    # clear in-memory cache and load from disk
    handlers._already_invited.clear()
    handlers._load_invite_cache()
    assert ("C2", "U1") in handlers._already_invited

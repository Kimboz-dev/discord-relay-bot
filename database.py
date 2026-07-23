import sqlite3
from contextlib import closing

DB_PATH = "relay.db"


def init_db():
    """Create the links table if it doesn't already exist."""
    with closing(sqlite3.connect(DB_PATH)) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS links (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_a_id INTEGER NOT NULL,
                guild_a_id INTEGER NOT NULL,
                channel_b_id INTEGER NOT NULL,
                guild_b_id INTEGER NOT NULL,
                link_type TEXT NOT NULL DEFAULT 'permanent',
                UNIQUE(channel_a_id, channel_b_id)
            )
        """)
        conn.commit()


def add_link(channel_a_id, guild_a_id, channel_b_id, guild_b_id, link_type="permanent"):
    """Create a bidirectional relay link between two channels.

    link_type is either 'permanent' (created with !link) or 'random'
    (created with !ucall matchmaking).
    """
    with closing(sqlite3.connect(DB_PATH)) as conn:
        conn.execute(
            "INSERT OR REPLACE INTO links "
            "(channel_a_id, guild_a_id, channel_b_id, guild_b_id, link_type) "
            "VALUES (?, ?, ?, ?, ?)",
            (channel_a_id, guild_a_id, channel_b_id, guild_b_id, link_type),
        )
        conn.commit()


def remove_links_for_channel(channel_id, link_type=None):
    """Delete links involving this channel.

    If link_type is None, removes ALL links (permanent and random).
    Otherwise only removes links of that specific type.
    """
    with closing(sqlite3.connect(DB_PATH)) as conn:
        if link_type is None:
            conn.execute(
                "DELETE FROM links WHERE channel_a_id = ? OR channel_b_id = ?",
                (channel_id, channel_id),
            )
        else:
            conn.execute(
                "DELETE FROM links WHERE (channel_a_id = ? OR channel_b_id = ?) "
                "AND link_type = ?",
                (channel_id, channel_id, link_type),
            )
        conn.commit()


def get_linked_channels(channel_id):
    """Return a list of channel IDs linked to the given channel (any type)."""
    with closing(sqlite3.connect(DB_PATH)) as conn:
        cur = conn.execute(
            "SELECT channel_b_id FROM links WHERE channel_a_id = ? "
            "UNION "
            "SELECT channel_a_id FROM links WHERE channel_b_id = ?",
            (channel_id, channel_id),
        )
        return [row[0] for row in cur.fetchall()]


def get_linked_channels_by_type(channel_id, link_type):
    """Return channel IDs linked to this channel, filtered to one link_type."""
    with closing(sqlite3.connect(DB_PATH)) as conn:
        cur = conn.execute(
            "SELECT channel_b_id FROM links WHERE channel_a_id = ? AND link_type = ? "
            "UNION "
            "SELECT channel_a_id FROM links WHERE channel_b_id = ? AND link_type = ?",
            (channel_id, link_type, channel_id, link_type),
        )
        return [row[0] for row in cur.fetchall()]


def get_links_for_guild(guild_id):
    """Return all link rows that involve the given guild."""
    with closing(sqlite3.connect(DB_PATH)) as conn:
        cur = conn.execute(
            "SELECT channel_a_id, guild_a_id, channel_b_id, guild_b_id, link_type "
            "FROM links WHERE guild_a_id = ? OR guild_b_id = ?",
            (guild_id, guild_id),
        )
        return cur.fetchall()

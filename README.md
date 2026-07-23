# Discord Cross-Server Relay Bot

A bot that links a channel in one Discord server to a channel in another
server, so messages sent in one automatically appear in the other —
complete with the sender's real name and avatar (via webhooks).

## What's in this folder

```
discord-relay-bot/
├── bot.py              # Main bot logic
├── database.py         # SQLite storage for channel links
├── requirements.txt    # Python dependencies
├── .env.example        # Template for your bot token
└── README.md           # This file
```

---

## Step 1 — Create the bot application

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications)
2. Click **New Application**, give it a name (e.g. "Relay Bot")
3. Go to the **Bot** tab (left sidebar) → click **Reset Token** (or it may already show one) → **Copy** the token
   - Keep this secret. Anyone with it can control your bot.
4. On the same **Bot** page, scroll to **Privileged Gateway Intents** and turn ON:
   - `MESSAGE CONTENT INTENT`

## Step 2 — Invite the bot to your servers

1. Go to **OAuth2 → URL Generator** (left sidebar)
2. Under **Scopes**, check: `bot`
3. Under **Bot Permissions**, check:
   - `Send Messages`
   - `Manage Webhooks`
   - `Read Message History`
   - `Embed Links`
   - `Attach Files`
4. Copy the URL generated at the bottom of the page, paste it into your browser, and choose a server to add the bot to
5. **Repeat step 4** for every server you want the bot in (you need "Manage Server" permission on each one, or the server owner needs to do it)

## Step 3 — Install Python requirements

Open a terminal in this folder (`discord-relay-bot/`) and run:

```bash
python -m venv venv
source venv/bin/activate        # on Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Step 4 — Add your bot token

1. Rename `.env.example` to `.env`
2. Open `.env` and paste your token from Step 1:

```
DISCORD_TOKEN=your_actual_token_here
```

## Step 5 — Run the bot

```bash
python bot.py
```

You should see:
```
Logged in as Relay Bot#1234 (ID: ...)
Connected to 2 server(s):
 - Server One (...)
 - Server Two (...)
Bot is ready.
```

If the bot doesn't appear online, double-check your token and that `MESSAGE CONTENT INTENT` is enabled (Step 1.4).

## Step 6 — Link two channels together

In **each** channel you want to connect, get its ID:

1. In Discord, go to **User Settings → Advanced** and enable **Developer Mode**
2. Right-click the channel → **Copy Channel ID**
   - Or just type `!myid` in the channel and the bot will reply with its ID

Then, in the **first** channel (e.g. `#general` in Server One), run:

```
!link <channel_id_of_the_other_channel>
```

Example:
```
!link 987654321098765432
```

The bot will confirm the link. From now on, any message sent in either
channel will appear in the other, tagged with the sender's name and server.

**Note:** You only need to run `!link` once, from either side — it creates
a two-way connection.

## Commands reference

| Command | Who can use it | What it does |
|---|---|---|
| `!link <channel_id>` | Manage Server permission | Permanently links this channel to another channel |
| `!unlink` | Manage Server permission | Removes permanent links for this channel |
| `!links` | Anyone | Lists active links for this server (shows type) |
| `!ucall` | Anyone | Joins a matchmaking queue and randomly connects to another server also waiting |
| `!cancel` | Anyone | Stops waiting in the `!ucall` queue |
| `!hangup` | Anyone | Ends the current random (`!ucall`) connection |
| `!myid` | Anyone | Shows the current channel's ID |

### How random matchmaking (`!ucall`) works

1. Someone types `!ucall` in a channel → the bot puts that channel in a waiting queue
2. When someone in a **different** server also types `!ucall`, the bot instantly
   links the two channels together and announces it in both
3. From that point, messages relay between the two channels just like a
   permanent `!link` — except either side can end it anytime with `!hangup`
4. If nobody else joins the queue within 2 minutes, the wait automatically
   cancels

This only works between servers where the bot is present, and only in
channels where someone actually ran `!ucall` — the bot never contacts a
server or channel on its own.

## Step 7 — Keep it running 24/7 (optional)

Right now the bot only runs while `python bot.py` is active on your
computer. To keep it online permanently, deploy it to a host such as:

- **Oracle Cloud Free Tier** (free, permanent VM)
- **Railway** or **Render** (free tier, then paid)
- **A small VPS** (DigitalOcean, Linode, ~$4–6/month)
- **A Raspberry Pi** left running at home

Whichever you choose, copy this whole folder to the server, install
requirements, set `DISCORD_TOKEN` as an environment variable (or `.env`
file), and run `python bot.py` — ideally inside a process manager like
`pm2`, `systemd`, or `screen`/`tmux` so it restarts if it crashes.

---

## Troubleshooting

- **"Missing permissions to relay into channel"** → The bot needs
  `Manage Webhooks` in the destination channel.
- **Messages aren't relaying** → Make sure `MESSAGE CONTENT INTENT` is
  enabled in the Developer Portal, and that you ran `!link` correctly.
- **`DISCORD_TOKEN not found`** → Make sure you renamed `.env.example`
  to `.env` (not `.env.example.env` or similar) and it's in the same
  folder as `bot.py`.

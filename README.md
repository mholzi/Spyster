# Spyster

### The Social Deduction Party Game That Runs on Your Smart Home

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2025.11+-blue.svg)](https://www.home-assistant.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> **Turn your Home Assistant into the ultimate party game server.** No apps to download. No accounts to create. No subscriptions. Just scan, play, and find the spy.

---

## What is Spyster?

Spyster is a **real-time multiplayer social deduction game** that runs entirely on your local Home Assistant instance. One player is secretly the Spy. Everyone else knows the secret location. Through clever questioning, players must identify the Spy before time runs out—while the Spy tries to blend in and figure out where they are.

**But here's the twist that makes Spyster different...**

### Confidence Betting: Where Every Vote Becomes a Story

In most social deduction games, voting is safe. You guess, you're right or wrong, next round.

**Not in Spyster.**

Before votes are revealed, every player secretly wagers **1, 2, or 3 points** on their vote being correct. Then comes the reveal—first the votes flip one by one, then the bets. That moment when you realize someone went **ALL IN** on a hunch? That's the tension other party games can't deliver.

- **Bet 1 point**: Safe play. +2 if right, -1 if wrong.
- **Bet 2 points**: Confident. +4 if right, -2 if wrong.
- **Bet 3 points (ALL IN)**: You're sure. +6 if right, -3 if wrong.

### The Double Agent Play

The Spy isn't just trying to survive—they're incentivized to **play bold**.

If the Spy goes ALL IN on framing an innocent player and the group convicts that innocent? **+10 bonus points**. Suddenly, looking "too confident" becomes suspicious. The meta-game writes itself.

---

## Why Host Game Night With Spyster?

| Traditional Party Games | Spyster |
|------------------------|---------|
| Pass the phone around | Everyone uses their own phone |
| Download an app | Just scan a QR code |
| Create accounts | No accounts, ever |
| Need internet | Runs on your local network |
| Same old voting | Confidence betting adds real stakes |
| Spy plays passive | Double Agent rewards bold plays |

**For the Home Assistant enthusiast who wants to be the ultimate party host.**

---

## Features

### Instant Setup
- **QR Code Join**: Display code on TV, guests scan and play in seconds
- **No App Required**: Works in any modern mobile browser
- **4-10 Players**: Perfect for small gatherings to full parties

### Real-Time Multiplayer
- **WebSocket Powered**: Instant state sync across all devices
- **Auto-Reconnection**: Phone died? Plug it in, you're back in the game
- **Session Persistence**: 5-minute reconnection window

### Polished Game Experience
- **Dramatic Reveals**: Staged vote and bet animations build tension
- **Round Timer**: Configurable questioning phase (default 7 minutes)
- **Multi-Round Games**: Play 3, 5, or more rounds with cumulative scoring
- **Leaderboard**: Track who's winning across the whole game night

### Host Display
- **TV-Optimized View**: Large text readable from across the room
- **Phase Indicators**: Everyone knows what's happening
- **Admin Controls**: Pause, skip, or end anytime

### Privacy-First Design
- **100% Local**: No cloud servers, no data leaves your network
- **No Accounts**: Players just enter a display name
- **Role Privacy**: Spy identity is never exposed in network traffic

---

## Screenshots

<!-- TODO: Add actual screenshots -->

| Host Display | Player View | Voting Phase |
|--------------|-------------|--------------|
| ![Host](docs/screenshots/host.png) | ![Player](docs/screenshots/player.png) | ![Vote](docs/screenshots/vote.png) |

---

## Installation

### HACS (Recommended)

1. Open **HACS** in your Home Assistant
2. Click the **three dots** menu → **Custom repositories**
3. Add this repository URL: `https://github.com/markusholzhaeuser/spyster`
4. Select category: **Integration**
5. Click **Add**
6. Search for **Spyster** and install
7. Restart Home Assistant
8. Add the integration via **Settings → Devices & Services → Add Integration → Spyster**

### Manual Installation

1. Download the latest release
2. Copy `custom_components/spyster` to your `config/custom_components/` directory
3. Restart Home Assistant
4. Add the integration via **Settings → Devices & Services → Add Integration → Spyster**

---

## Quick Start

### 1. Start a Game Session

Navigate to your Spyster panel in Home Assistant. A QR code will appear on screen.

### 2. Players Join

Guests connect to your WiFi and scan the QR code with their phone camera. They enter a display name and tap Join.

### 3. Configure & Start

Once 4-10 players have joined:
- Choose a location pack (Classic included)
- Set round duration (default: 7 minutes)
- Set number of rounds (default: 5)
- Hit **START**

### 4. Play!

- **Non-Spy Players**: See the location and your role. Answer questions without giving it away.
- **The Spy**: See possible locations but not the actual one. Blend in. Figure it out.
- **Anyone**: Call a vote when you're suspicious!

### 5. Vote & Bet

When voting is called:
1. Select who you think is the Spy
2. Choose your confidence bet (1, 2, or ALL IN)
3. Lock it in
4. Watch the dramatic reveal

---

## How Scoring Works

| Action | Points |
|--------|--------|
| Correct vote, bet 1 | +2 |
| Correct vote, bet 2 | +4 |
| Correct vote, bet 3 (ALL IN) | +6 |
| Wrong vote, bet 1 | -1 |
| Wrong vote, bet 2 | -2 |
| Wrong vote, bet 3 (ALL IN) | -3 |
| Spy: Correct location guess | +4 |
| Spy: ALL IN frame succeeds (Double Agent) | +10 |

**Ties in voting?** No one is convicted. The Spy survives another round.

---

## Content Packs

### Classic (Included)
10 locations with 6-8 roles each:
- Beach, Hospital, School, Restaurant, Airport, Casino, Movie Studio, Submarine, Space Station, Circus

*More packs coming in future updates!*

---

## Requirements

- **Home Assistant**: 2025.11 or newer
- **Network**: All players must be on the same local network
- **Browsers**: Chrome, Safari, or Firefox (last 2 years)

---

## Troubleshooting

### "Unable to connect" when scanning QR code
- Make sure the player is on **WiFi**, not cellular data
- Verify they're on the **same network** as Home Assistant
- Try a different browser (Chrome works best)

### Player shows "disconnected" in lobby
- If they closed their browser, they can rescan to rejoin
- Host can remove ghost sessions after 60 seconds
- Players have 5 minutes to reconnect before their session expires

### Game feels laggy
- Check your Home Assistant server load
- Ensure all players have strong WiFi signal
- WebSocket works best on local network (no VPN)

---

## Roadmap

### Coming Soon
- Additional content packs (Home, Sci-Fi, Fantasy)
- 2-Spy mode for larger groups (8+ players)
- Custom location & role creation

### Future Vision
- Cross-household play via cloud relay
- AI Spy for solo practice
- Tournament mode
- Achievement system

---

## Contributing

Contributions are welcome! Please read our contributing guidelines before submitting PRs.

---

## Support

- **Issues**: [GitHub Issues](https://github.com/markusholzhaeuser/spyster/issues)
- **Discussions**: [GitHub Discussions](https://github.com/markusholzhaeuser/spyster/discussions)

---

## License

MIT License - see [LICENSE](LICENSE) for details.

---

## Credits

Built with love for game nights everywhere.

Inspired by Spyfall, enhanced with original mechanics that make every vote matter.

---

<p align="center">
  <strong>Ready to become the ultimate party host?</strong><br>
  <a href="#installation">Install Spyster Now</a>
</p>

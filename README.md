# Space Invaders

A Python recreation of the classic arcade game, built with Pygame. Made by both [Averi Wylie] and [Shahyar Anfaz].(https://www.linkedin.com/in/shahyaranfaz/).

The game features fully custom graphics, 8-directional player movement, dynamic enemy spawning, a power-up system, and a complete user system with leaderboards, personal profiles, and friends — all backed by a local SQLite database.

---

## Features

- 8-directional player movement with direction-matched spaceship sprites
- Enemy invaders with speed scaling tied to kill thresholds
- Projectile mechanics with shooting cooldown and piercing ammo power-up
- Score and kill tracking, with a win condition at 999,999 points
- Timed power-ups: double movement speed, double shooting speed, double score, piercing ammo
- Full user system: register, login, or play locally without an account
- SQLite-backed score persistence with kills tracked alongside score
- Leaderboard system: global top 1000, local scores, and friends leaderboard
- Personal profile showing personal best, kill count, and full score history
- Friends system — add friends by username, view a friends-only leaderboard

---

## On the Leaderboard System

Scores are stored in a local SQLite database (`assets/scores.db`). The "global" leaderboard aggregates all registered user scores on the machine running the game — it is not networked across separate installations. A true internet-connected leaderboard would require a hosted server and database, which is outside the scope of this project. The distinction between global and local scores is preserved in the schema so the system could be extended to a networked backend without restructuring the data model.

- **Logged-in play:** scores are stored against your account and appear on the leaderboard and your profile
- **Local play:** scores are stored anonymously and visible only under Local Scores on that machine

---

## Getting Started

### Prerequisites

- Python 3.9+
- Pygame

### Installation

```bash
git clone https://github.com/AveriWylie/Project-1---Space-Invaders.git
cd Project-1---Space-Invaders
pip install pygame
python application.py
```

The database is created automatically at `assets/scores.db` on first run. No setup required.

---

## How It Works

### Movement

Player input is captured as a 4-tuple of held keys `(L, R, U, D)` mapped to one of 8 movement directions or no movement. Each direction maps to a movement coefficient pair and a corresponding sprite, so the ship always faces the direction it is moving.

### Enemy Spawning

Enemy spawn rate is controlled by kill thresholds defined in `constants.py`. As the player's kill count crosses each threshold, the number of active enemies increases. Enemies move toward the player and trigger game over on contact.

### Power-ups

Power-up tokens spawn at random during gameplay and are collected on contact. Each applies a timed 30-second effect. Only one power-up can be active at a time. Active power-up state is shown in the HUD.

| Power-up | Effect |
|---|---|
| Double Movement Speed | 2x player movement speed |
| Double Shooting Speed | Halved shooting cooldown |
| Double Score | 2x score per action |
| Piercing Ammo | Bullets pass through multiple enemies |

### Score and User System

On startup the player chooses to log in, register, or play locally. Scores are written to `assets/scores.db` at game over.

The database schema:

```
users       — id, username, password (sha256 hashed)
scores      — id, user_id, username, score, kills, date, time, is_local
friendships — id, user_id, friend_id
```

Friends are added by username. The friends leaderboard shows each friend's personal best score, ranked highest to lowest.

---

## Project Structure

```
Space-Invaders/
├── assets/
│   ├── character_icons/    # Directional spaceship sprites
│   ├── token_icons/        # Score, ammo, and power-up token sprites
│   ├── fonts/              # Game and logo fonts
│   ├── game_background.png
│   └── scores.db           # SQLite database (created on first run)
├── application.py          # Main game loop, UI screens, database layer
├── interface.py            # Button and ScrollArea UI classes
├── character.py            # Player, enemy, bullet classes
├── constants.py            # Screen size, fonts, movement and spawn config
├── game_token.py           # Token and power-up logic
└── README.md
```

---

## License

MIT License. See [LICENSE](https://github.com/AveriWylie/Project-1---Space-Invaders/blob/main/LICENSE) for details.

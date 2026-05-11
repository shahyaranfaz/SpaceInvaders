from __future__ import annotations
import sys
import sqlite3
import hashlib
import datetime
import pygame
from character import UserPlayer
from interface import Button, ScrollArea
from constants import *


# ─────────────────────────────────────────────
# DATABASE
# ─────────────────────────────────────────────

DB_PATH = "assets/scores.db"


def get_conn():
    return sqlite3.connect(DB_PATH)


def init_db():
    conn = get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT    UNIQUE NOT NULL,
            password TEXT    NOT NULL
        );
        CREATE TABLE IF NOT EXISTS scores (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id  INTEGER,
            username TEXT,
            score    INTEGER NOT NULL,
            kills    INTEGER NOT NULL,
            date     TEXT    NOT NULL,
            time     TEXT    NOT NULL,
            is_local INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS friendships (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id   INTEGER NOT NULL,
            friend_id INTEGER NOT NULL,
            UNIQUE(user_id, friend_id)
        );
    """)
    conn.commit()
    conn.close()


def hash_pw(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def register_user(username: str, password: str):
    try:
        conn = get_conn()
        conn.execute("INSERT INTO users (username, password) VALUES (?, ?)",
                     (username, hash_pw(password)))
        conn.commit()
        conn.close()
        return None
    except sqlite3.IntegrityError:
        return "Username already taken."


def login_user(username: str, password: str):
    conn = get_conn()
    row = conn.execute(
        "SELECT id, username FROM users WHERE username=? AND password=?",
        (username, hash_pw(password))
    ).fetchone()
    conn.close()
    return row


def record_score(score: int, kills: int, user=None) -> bool:
    """Insert score into DB. Returns True if it is the user's new personal best."""
    now = datetime.datetime.now()
    conn = get_conn()
    if user:
        conn.execute(
            "INSERT INTO scores (user_id, username, score, kills, date, time, is_local) VALUES (?,?,?,?,?,?,0)",
            (user[0], user[1], score, kills, now.strftime("%Y-%m-%d"), now.strftime("%H:%M:%S"))
        )
        conn.commit()
        best = conn.execute(
            "SELECT MAX(score) FROM scores WHERE user_id=? AND is_local=0", (user[0],)
        ).fetchone()[0]
        conn.close()
        return score >= best
    else:
        conn.execute(
            "INSERT INTO scores (user_id, username, score, kills, date, time, is_local) VALUES (NULL,'LOCAL',?,?,?,?,1)",
            (score, kills, now.strftime("%Y-%m-%d"), now.strftime("%H:%M:%S"))
        )
        conn.commit()
        conn.close()
        return False


def get_global_leaderboard(limit=1000):
    conn = get_conn()
    rows = conn.execute(
        "SELECT username, score, kills, date, time FROM scores WHERE is_local=0 ORDER BY score DESC LIMIT ?",
        (limit,)
    ).fetchall()
    conn.close()
    return rows


def get_personal_scores(user_id: int):
    conn = get_conn()
    rows = conn.execute(
        "SELECT score, kills, date, time FROM scores WHERE user_id=? ORDER BY score DESC",
        (user_id,)
    ).fetchall()
    conn.close()
    return rows


def get_local_scores():
    conn = get_conn()
    rows = conn.execute(
        "SELECT score, kills, date, time FROM scores WHERE is_local=1 ORDER BY score DESC"
    ).fetchall()
    conn.close()
    return rows


def get_friends(user_id: int):
    conn = get_conn()
    rows = conn.execute(
        """SELECT u.id, u.username FROM friendships f
           JOIN users u ON u.id = f.friend_id
           WHERE f.user_id=?""", (user_id,)
    ).fetchall()
    conn.close()
    return rows


def add_friend(user_id: int, friend_username: str):
    conn = get_conn()
    friend = conn.execute("SELECT id FROM users WHERE username=?", (friend_username,)).fetchone()
    if not friend:
        conn.close()
        return "User not found."
    if friend[0] == user_id:
        conn.close()
        return "You cannot add yourself."
    try:
        conn.execute("INSERT INTO friendships (user_id, friend_id) VALUES (?,?)", (user_id, friend[0]))
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        return "Already friends."
    conn.close()
    return None


def get_friends_leaderboard(user_id: int):
    friends = get_friends(user_id)
    friend_ids = [f[0] for f in friends] + [user_id]
    placeholders = ",".join("?" * len(friend_ids))
    conn = get_conn()
    rows = conn.execute(
        f"""SELECT username, MAX(score) as best, date, time
            FROM scores WHERE user_id IN ({placeholders}) AND is_local=0
            GROUP BY user_id ORDER BY best DESC""",
        friend_ids
    ).fetchall()
    conn.close()
    return rows


# ─────────────────────────────────────────────
# SESSION STATE
# ─────────────────────────────────────────────

current_user = None  # (id, username) or None


# ─────────────────────────────────────────────
# CORE HELPERS
# ─────────────────────────────────────────────

def render_logo(y_frac=0.12):
    rendered = FONT_LOGO.render("SPACE INVADERS", True, "White")
    screen.blit(rendered, rendered.get_rect(center=(SCREEN_WIDTH // 2, int(SCREEN_HEIGHT * y_frac))))


def handle_events(buttons: list[Button], player: UserPlayer = None,
                  scroll: ScrollArea = None) -> None:
    """Update and draw each button in <buttons>, manage user inputs if
    <player> is provided, and manage scrolling if <scroll> is provided.
    """
    mouse_pos = pygame.mouse.get_pos()
    for button in buttons:
        button.change_colour(mouse_pos)
        button.draw(screen)
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            quit_actions()
        if event.type == pygame.MOUSEBUTTONDOWN:
            for button in buttons:
                if button.check_for_input(mouse_pos):
                    button.action()
        if player and event.type in (pygame.KEYDOWN, pygame.KEYUP):
            is_keydown = event.type == pygame.KEYDOWN
            if event.key in KEY_STROKES:
                player.set_user_input(event.key, is_keydown)
            elif event.key == pygame.K_SPACE:
                player.set_shooting(is_keydown)
        if scroll:
            scroll.handle_event(event)


def update_screen() -> None:
    """Update the display and enforce a frame rate of 60 FPS."""
    pygame.display.update()
    clock.tick(60)


def quit_actions() -> None:
    """Quit the Pygame application and exit the program."""
    pygame.quit()
    sys.exit()


def display_hud(player: UserPlayer) -> None:
    """Draw <player>'s HUD on the screen, including score, ammo count, and
    active power-ups.
    """
    score_text = FONT_25.render(f"SCORE: {player.score:06}", True, (255, 255, 255))
    screen.blit(score_text, score_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 15)))
    ammo_text = FONT_85.render(f"{player.ammo:3}", True, AMMO_COLOURS.get(player.ammo, (255, 255, 255)))
    screen.blit(ammo_text, ammo_text.get_rect(topright=(SCREEN_WIDTH - 10, 10)))
    if player.power_up is not None:
        power_up_text = FONT_40.render(str(player.power_up), True, (255, 255, 255))
        screen.blit(power_up_text, power_up_text.get_rect(topleft=(10, 10)))


# ─────────────────────────────────────────────
# TEXT INPUT
# ─────────────────────────────────────────────

def text_input_screen(title: str, fields: list[str], mask: list[bool] = None):
    """Generic text input screen matching the game aesthetic.
    Returns dict {field: value} on submit, None on back.
    """
    if mask is None:
        mask = [False] * len(fields)
    values = {f: "" for f in fields}
    active = 0
    error_msg = ""

    while True:
        screen.fill("Black")
        render_logo()

        title_surf = FONT_60.render(title, True, "White")
        screen.blit(title_surf, title_surf.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT * 0.28)))

        for i, field in enumerate(fields):
            y = SCREEN_HEIGHT // 2 - (len(fields) - 1) * 35 + i * 70
            label = FONT_40.render(field + ":", True, "White")
            screen.blit(label, label.get_rect(midright=(SCREEN_WIDTH // 2 - 10, y)))
            display = ("*" * len(values[field])) if mask[i] else values[field]
            box_color = "Gold" if i == active else "White"
            val_surf = FONT_40.render(display + ("|" if i == active else ""), True, box_color)
            screen.blit(val_surf, val_surf.get_rect(midleft=(SCREEN_WIDTH // 2 + 10, y)))

        if error_msg:
            err_surf = FONT_25.render(error_msg, True, "Red")
            screen.blit(err_surf, err_surf.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + len(fields) * 70 - 10)))

        submit_y = SCREEN_HEIGHT // 2 + len(fields) * 70 + 40
        back_y = submit_y + 70
        submit_btn = Button((SCREEN_WIDTH // 2, submit_y), "SUBMIT", FONT_50, "White", "Green", lambda: None)
        back_btn = Button((SCREEN_WIDTH // 2, back_y), "BACK", FONT_50, "White", "Red", lambda: None)

        mouse_pos = pygame.mouse.get_pos()
        submit_btn.change_colour(mouse_pos)
        submit_btn.draw(screen)
        back_btn.change_colour(mouse_pos)
        back_btn.draw(screen)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                quit_actions()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_TAB:
                    active = (active + 1) % len(fields)
                elif event.key == pygame.K_RETURN:
                    if all(values[f].strip() for f in fields):
                        return values
                    else:
                        error_msg = "All fields required."
                elif event.key == pygame.K_BACKSPACE:
                    values[fields[active]] = values[fields[active]][:-1]
                else:
                    if len(values[fields[active]]) < 24:
                        values[fields[active]] += event.unicode
            if event.type == pygame.MOUSEBUTTONDOWN:
                if submit_btn.check_for_input(mouse_pos):
                    if all(values[f].strip() for f in fields):
                        return values
                    else:
                        error_msg = "All fields required."
                if back_btn.check_for_input(mouse_pos):
                    return None

        update_screen()


# ─────────────────────────────────────────────
# AUTH
# ─────────────────────────────────────────────

def login_screen():
    global current_user
    result = text_input_screen("LOGIN", ["Username", "Password"], mask=[False, True])
    if result is None:
        startup_screen()
        return
    user = login_user(result["Username"], result["Password"])
    if user:
        current_user = user
        main_menu()
    else:
        error_screen("Invalid username or password.", login_screen, startup_screen)


def register_screen():
    result = text_input_screen("REGISTER", ["Username", "Password", "Confirm"], mask=[False, True, True])
    if result is None:
        startup_screen()
        return
    if result["Password"] != result["Confirm"]:
        error_screen("Passwords do not match.", register_screen, startup_screen)
        return
    err = register_user(result["Username"], result["Password"])
    if err:
        error_screen(err, register_screen, startup_screen)
    else:
        global current_user
        current_user = login_user(result["Username"], result["Password"])
        success_screen(f"Welcome, {result['Username']}!", main_menu)


def error_screen(msg: str, retry_action, back_action):
    while True:
        screen.fill("Black")
        render_logo()
        err_surf = FONT_50.render(msg, True, "Red")
        screen.blit(err_surf, err_surf.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)))
        retry_btn = Button((SCREEN_WIDTH // 2 - 150, SCREEN_HEIGHT // 2 + 80), "RETRY", FONT_50, "White", "Green", retry_action)
        back_btn  = Button((SCREEN_WIDTH // 2 + 150, SCREEN_HEIGHT // 2 + 80), "BACK",  FONT_50, "White", "Red",   back_action)
        handle_events([retry_btn, back_btn])
        update_screen()


def success_screen(msg: str, next_action):
    while True:
        screen.fill("Black")
        render_logo()
        surf = FONT_50.render(msg, True, "Green")
        screen.blit(surf, surf.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)))
        cont_btn = Button((SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 80), "CONTINUE", FONT_50, "White", "Green", next_action)
        handle_events([cont_btn])
        update_screen()


# ─────────────────────────────────────────────
# STARTUP
# ─────────────────────────────────────────────

def startup_screen():
    global current_user
    current_user = None
    while True:
        screen.fill("Black")
        render_logo(0.2)
        login_btn    = Button((SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 60),  "LOGIN",        FONT_60, "White", "Gold",  login_screen)
        register_btn = Button((SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 20),  "REGISTER",     FONT_60, "White", "Green", register_screen)
        local_btn    = Button((SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 100), "PLAY LOCALLY", FONT_50, "White", "White", main_menu)
        quit_btn     = Button((SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 175), "QUIT",         FONT_50, "White", "Red",   quit_actions)
        handle_events([login_btn, register_btn, local_btn, quit_btn])
        update_screen()


# ─────────────────────────────────────────────
# MAIN MENU
# ─────────────────────────────────────────────

def main_menu() -> None:
    """Display the main menu screen. Loops until the user selects an action."""
    while True:
        screen.fill("Black")
        render_logo()
        if current_user:
            user_surf = FONT_25.render(f"Logged in as: {current_user[1]}", True, "Gold")
            screen.blit(user_surf, user_surf.get_rect(topright=(SCREEN_WIDTH - 20, 20)))

        buttons = [
            Button((SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 80), "PLAY",         FONT_60, "White", "Green", play),
            Button((SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2),      "LEADERBOARDS", FONT_50, "White", "Gold",  leaderboard_menu),
        ]
        if current_user:
            buttons += [
                Button((SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 75),  "MY PROFILE", FONT_50, "White", "White", my_profile),
                Button((SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 145), "FRIENDS",    FONT_50, "White", "White", friends_menu),
                Button((SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 215), "LOG OUT",    FONT_40, "White", "Red",   startup_screen),
            ]
        else:
            buttons.append(Button((SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 75), "LOG IN / REGISTER", FONT_50, "White", "Gold", startup_screen))

        buttons.append(Button((SCREEN_WIDTH // 2, SCREEN_HEIGHT - 30), "QUIT", FONT_40, "White", "Red", quit_actions))
        handle_events(buttons)
        update_screen()


# ─────────────────────────────────────────────
# LEADERBOARDS
# ─────────────────────────────────────────────

def leaderboard_menu():
    while True:
        screen.fill("Black")
        render_logo()
        buttons = [
            Button((SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 80), "GLOBAL TOP 1000",     FONT_50, "White", "Gold",  show_global_leaderboard),
            Button((SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2),       "LOCAL SCORES",        FONT_50, "White", "White", show_local_scores),
        ]
        if current_user:
            buttons.append(Button((SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 80), "FRIENDS LEADERBOARD", FONT_50, "White", "White", show_friends_leaderboard))
        buttons.append(Button((SCREEN_WIDTH - 80, SCREEN_HEIGHT - 20), "BACK", FONT_50, "White", "Red", main_menu))
        handle_events(buttons)
        update_screen()


def show_score_list(title: str, rows: list, columns: list[str], back_action):
    """Display a scrollable list of scores."""
    header = "  ".join(f"{c:<14}" for c in columns)
    lines = [header] + ["  ".join(f"{str(v):<14}" for v in row) for row in rows]
    content_h = max(len(lines) * 45, SCREEN_HEIGHT)
    scroll_area = ScrollArea(0, 120, SCREEN_WIDTH, SCREEN_HEIGHT - 120, content_h)
    scroll_area.surface.fill("Black")
    for i, line in enumerate(lines):
        colour = "Gold" if i == 0 else "White"
        surf = FONT_40.render(line, True, colour)
        rect = surf.get_rect(center=(scroll_area.rect.width // 2, i * 45 + 22))
        scroll_area.surface.blit(surf, rect)
    back_btn = Button((SCREEN_WIDTH - 80, SCREEN_HEIGHT - 20), "BACK", FONT_50, "White", "Red", back_action)
    while True:
        screen.fill("Black")
        title_surf = FONT_60.render(title, True, "White")
        screen.blit(title_surf, title_surf.get_rect(center=(SCREEN_WIDTH // 2, 60)))
        scroll_area.draw(screen)
        handle_events([back_btn], scroll=scroll_area)
        update_screen()


def show_global_leaderboard():
    rows = get_global_leaderboard(1000)
    ranked = [(i + 1, r[0], r[1], r[2], r[3], r[4]) for i, r in enumerate(rows)]
    show_score_list("GLOBAL TOP 1000", ranked, ["#", "Player", "Score", "Kills", "Date", "Time"], leaderboard_menu)


def show_local_scores():
    rows = get_local_scores()
    show_score_list("LOCAL SCORES", rows, ["Score", "Kills", "Date", "Time"], leaderboard_menu)


def show_friends_leaderboard():
    if not current_user:
        return
    rows = get_friends_leaderboard(current_user[0])
    ranked = [(i + 1, r[0], r[1], r[2], r[3]) for i, r in enumerate(rows)]
    show_score_list("FRIENDS LEADERBOARD", ranked, ["#", "Player", "Best", "Date", "Time"], leaderboard_menu)


# ─────────────────────────────────────────────
# PROFILE
# ─────────────────────────────────────────────

def my_profile():
    if not current_user:
        return
    rows = get_personal_scores(current_user[0])
    best = rows[0][0] if rows else 0
    best_kills = rows[0][1] if rows else 0
    while True:
        screen.fill("Black")
        render_logo(0.08)
        name_surf = FONT_60.render(current_user[1], True, "Gold")
        screen.blit(name_surf, name_surf.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT * 0.22)))
        best_surf = FONT_50.render(f"Personal Best: {best:,}  ({best_kills} kills)", True, "White")
        screen.blit(best_surf, best_surf.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT * 0.32)))
        games_surf = FONT_40.render(f"Games Played: {len(rows)}", True, "White")
        screen.blit(games_surf, games_surf.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT * 0.40)))
        history_btn = Button((SCREEN_WIDTH // 2 - 150, SCREEN_HEIGHT * 0.52), "SCORE HISTORY", FONT_50, "White", "Gold",
                             lambda: show_score_list("MY SCORES", rows, ["Score", "Kills", "Date", "Time"], my_profile))
        back_btn = Button((SCREEN_WIDTH // 2 + 150, SCREEN_HEIGHT * 0.52), "BACK", FONT_50, "White", "Red", main_menu)
        handle_events([history_btn, back_btn])
        update_screen()


# ─────────────────────────────────────────────
# FRIENDS
# ─────────────────────────────────────────────

def friends_menu():
    if not current_user:
        return
    friends = get_friends(current_user[0])
    while True:
        screen.fill("Black")
        render_logo(0.08)
        friends_surf = FONT_50.render(f"Friends ({len(friends)})", True, "White")
        screen.blit(friends_surf, friends_surf.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT * 0.25)))
        for i, f in enumerate(friends[:10]):
            f_surf = FONT_40.render(f[1], True, "Gold")
            screen.blit(f_surf, f_surf.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT * 0.33 + i * 45)))
        add_btn  = Button((SCREEN_WIDTH // 2 - 150, SCREEN_HEIGHT * 0.80), "ADD FRIEND", FONT_50, "White", "Green", add_friend_screen)
        back_btn = Button((SCREEN_WIDTH // 2 + 150, SCREEN_HEIGHT * 0.80), "BACK",       FONT_50, "White", "Red",   main_menu)
        handle_events([add_btn, back_btn])
        update_screen()


def add_friend_screen():
    result = text_input_screen("ADD FRIEND", ["Username"])
    if result is None:
        friends_menu()
        return
    err = add_friend(current_user[0], result["Username"])
    if err:
        error_screen(err, add_friend_screen, friends_menu)
    else:
        friends_menu()


# ─────────────────────────────────────────────
# GAMEPLAY
# ─────────────────────────────────────────────

def play() -> None:
    """Run the main game loop. Handles player shooting, enemy updates, token
    collection, HUD updates, and checks for game-over conditions.
    """
    buttons = [Button((SCREEN_WIDTH / 2, 25), "PRESS TO QUIT", FONT_25, "White", "Red", quit_actions)]
    player = UserPlayer(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2)
    enemies = []
    tokens = []
    while True:
        screen.blit(BACKGROUND, (0, 0))
        display_hud(player)
        handle_events(buttons, player)
        if player.shooting:
            player.shoot()
        for bullet in player.bullets.copy():
            bullet.place(screen)
        for enemy in enemies.copy():
            if enemy.check_for_death(player):
                game_over(player, enemies + player.bullets + tokens)
                return None
            enemy.place(screen)
        for token in tokens.copy():
            token.draw(screen)
            token.collect(player, tokens)
        player.place(screen)
        player.check_for_kills(enemies)
        player.set_enemy_count(enemies)
        player.update_tokens(tokens)
        player.update_score()
        update_screen()
        if player.score >= 999999:
            game_over(player, enemies + player.bullets + tokens)


def game_over(player: UserPlayer, objects: list) -> None:
    """Record score, display outcome screen, and return to main menu."""
    new_high_score = record_score(player.score, player.kills, current_user)
    if player.score >= 999999:
        display_msg, colour = "You Won!", "Gold"
    elif new_high_score:
        display_msg, colour = "New High Score!", "Green"
    else:
        display_msg, colour = "You Lost!", "Red"
    buttons = [Button((SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 + 100), "MAIN MENU", FONT_60, "White", "Green", main_menu)]
    screen.blit(BACKGROUND, (0, 0))
    for obj in objects:
        obj.draw(screen)
    player.draw(screen)
    while True:
        rendered_text = FONT_100.render(display_msg, True, colour)
        screen.blit(rendered_text, rendered_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)))
        handle_events(buttons)
        update_screen()


# ─────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────

if __name__ == "__main__":
    pygame.init()
    screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
    pygame.display.set_caption("Space Invaders")
    clock = pygame.time.Clock()
    init_db()
    startup_screen()

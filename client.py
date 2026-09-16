import json
import math
import random
import sys
import pygame
import websocket

# --- Initialize Display & Virtual TV Canvas ---
pygame.init()
WIN_WIDTH, WIN_HEIGHT = 1000, 600
screen = pygame.display.set_mode((WIN_WIDTH, WIN_HEIGHT), pygame.RESIZABLE)
pygame.display.set_caption("AstraClash")
clock = pygame.time.Clock()

V_WIDTH, V_HEIGHT = 1000, 600
virtual_canvas = pygame.Surface((V_WIDTH, V_HEIGHT))

font = pygame.font.SysFont("consolas", 13)
font_large = pygame.font.SysFont("consolas", 18, bold=True)
title_font = pygame.font.SysFont("consolas", 36, bold=True)

# 6 Rainbow Colors
RAINBOW = {
    1: (255, 60, 60),    # Red
    2: (255, 140, 30),   # Orange
    3: (255, 220, 50),   # Yellow
    4: (50, 255, 80),    # Green
    5: (30, 140, 255),   # Blue
    6: (190, 70, 255)    # Violet
}

BLACK = (10, 10, 25)
WHITE = (255, 255, 255)
CYAN = (0, 255, 255)
LASER_RED = (255, 50, 50)
GRAY = (140, 140, 150)
DARK_GRAY = (45, 50, 65)
XP_BG = (20, 30, 50)
XP_BLUE = (0, 180, 255)
ORE_BLUE = (0, 215, 255)
ASTEROID_COLOR = (115, 110, 125)
ORE_ASTEROID_COLOR = (70, 95, 130)
PANEL_BG = (15, 18, 32)

RENDER_URL = "wss://astraclash-howt.onrender.com"
ws = None

# Background Starfield
stars = [[random.randint(0, V_WIDTH), random.randint(0, V_HEIGHT), random.uniform(0.5, 1.8)] for _ in range(90)]

def draw_starfield(surf, w, h):
    for s in stars:
        s[1] = (s[1] + s[2] * 0.3) % h
        s[0] = (s[0] + s[2] * 0.08) % w
        val = int(min(255, s[2] * 120))
        pygame.draw.circle(surf, (val, val, val + 15), (int(s[0]), int(s[1])), int(s[2]))

def draw_card(surf, rect, border_color=CYAN):
    pygame.draw.rect(surf, PANEL_BG, rect, border_radius=6)
    pygame.draw.rect(surf, border_color, rect, 2, border_radius=6)

def get_canvas_mouse_pos():
    win_w, win_h = screen.get_size()
    scale = min(win_w / V_WIDTH, win_h / V_HEIGHT)
    scaled_w = int(V_WIDTH * scale)
    scaled_h = int(V_HEIGHT * scale)
    offset_x = (win_w - scaled_w) // 2
    offset_y = (win_h - scaled_h) // 2

    mx, my = pygame.mouse.get_pos()
    cx = (mx - offset_x) / scale if scale != 0 else 0
    cy = (my - offset_y) / scale if scale != 0 else 0
    return cx, cy

def present_frame():
    screen.fill((0, 0, 0))
    win_w, win_h = screen.get_size()
    scale = min(win_w / V_WIDTH, win_h / V_HEIGHT)
    scaled_w = int(V_WIDTH * scale)
    scaled_h = int(V_HEIGHT * scale)
    offset_x = (win_w - scaled_w) // 2
    offset_y = (win_h - scaled_h) // 2

    scaled_surf = pygame.transform.scale(virtual_canvas, (scaled_w, scaled_h))
    screen.blit(scaled_surf, (offset_x, offset_y))
    pygame.display.flip()

# --- Matchmaking Lobby ---
menu_mode = "main"
status_message = "Connecting to matchmaking server..."
status_color = RAINBOW[3]

room_code_input = ""
password_input = ""
active_input = "code"

my_id = 1
room_code = ""

def connect_ws():
    global ws, status_message, status_color
    if ws is not None:
        return True
    try:
        ws = websocket.create_connection(RENDER_URL, timeout=45)
        ws.settimeout(0.001)
        status_message = "Connected to Render. Choose game mode."
        status_color = RAINBOW[4]
        return True
    except Exception as e:
        status_message = f"Connection error: {e}"
        status_color = RAINBOW[1]
        return False

connect_ws()

def send_msg(payload):
    if ws:
        try:
            ws.send(json.dumps(payload))
        except Exception:
            pass

def poll_msg():
    if not ws:
        return None
    try:
        raw = ws.recv()
        if raw:
            return json.loads(raw)
    except Exception:
        return None
    return None

in_lobby = True
while in_lobby:
    mouse_pos = get_canvas_mouse_pos()
    mouse_click = False

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            if ws:
                ws.close()
            pygame.quit()
            sys.exit()
        elif event.type == pygame.VIDEORESIZE:
            screen = pygame.display.set_mode((event.w, event.h), pygame.RESIZABLE)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mouse_click = True
        elif event.type == pygame.KEYDOWN:
            if menu_mode in ("host_private", "join_private"):
                if event.key == pygame.K_BACKSPACE:
                    if active_input == "code":
                        room_code_input = room_code_input[:-1]
                    else:
                        password_input = password_input[:-1]
                elif event.key == pygame.K_TAB:
                    active_input = "pass" if active_input == "code" else "code"
                elif event.unicode.isprintable():
                    if active_input == "code" and len(room_code_input) < 4:
                        room_code_input += event.unicode.upper()
                    elif active_input == "pass" and len(password_input) < 16:
                        password_input += event.unicode

    msg = poll_msg()
    if msg:
        action = msg.get("action")
        status = msg.get("status")

        if action == "player_joined" or (menu_mode == "waiting" and action == "player_joined"):
            in_lobby = False
        elif status == "ok":
            my_id = msg.get("player_id", 1)
            room_code = msg.get("room_code", "")
            if "rooms" in msg:
                rooms = msg["rooms"]
                if rooms:
                    send_msg({"action": "join_room", "room_code": rooms[0], "password": None})
                    status_message = "Joining public arena..."
                else:
                    send_msg({"action": "create_room", "public": True, "password": None})
                    status_message = "Created public room. Waiting for pilots..."
                    menu_mode = "waiting"
            elif menu_mode == "waiting":
                status_message = f"Room [{room_code}] open. Waiting for pilots (Up to 6)..."
            elif my_id > 1:
                in_lobby = False
        elif status == "error":
            status_message = msg.get("msg", "Action failed.")
            status_color = RAINBOW[1]
            menu_mode = "main"

    virtual_canvas.fill(BLACK)
    draw_starfield(virtual_canvas, V_WIDTH, V_HEIGHT)

    t_surf = title_font.render("A S T R A C L A S H", True, CYAN)
    virtual_canvas.blit(t_surf, (V_WIDTH // 2 - t_surf.get_width() // 2, 70))
    sub_surf = font.render("6-PLAYER RAINBOW ORBITAL ARENA", True, GRAY)
    virtual_canvas.blit(sub_surf, (V_WIDTH // 2 - sub_surf.get_width() // 2, 115))

    cx = V_WIDTH // 2

    if menu_mode == "main":
        buttons = [
            ("QUICK PLAY (PUBLIC)", 190, CYAN),
            ("HOST PRIVATE ROOM", 260, WHITE),
            ("JOIN PRIVATE ROOM", 330, WHITE)
        ]
        for label, y, base_col in buttons:
            b_rect = pygame.Rect(cx - 150, y, 300, 48)
            hover = b_rect.collidepoint(mouse_pos)
            col = CYAN if hover else base_col
            draw_card(virtual_canvas, b_rect, col)
            lbl = font_large.render(label, True, col)
            virtual_canvas.blit(lbl, (cx - lbl.get_width() // 2, y + 14))

            if hover and mouse_click and connect_ws():
                if label.startswith("QUICK"):
                    send_msg({"action": "list_public"})
                    status_message = "Searching public games..."
                    status_color = RAINBOW[3]
                elif label.startswith("HOST"):
                    menu_mode = "host_private"
                    password_input = ""
                    active_input = "pass"
                elif label.startswith("JOIN"):
                    menu_mode = "join_private"
                    room_code_input = ""
                    password_input = ""
                    active_input = "code"

    elif menu_mode == "host_private":
        card_rect = pygame.Rect(cx - 170, 190, 340, 220)
        draw_card(virtual_canvas, card_rect, CYAN)

        lbl = font_large.render("HOST PRIVATE ROOM (MAX 6)", True, CYAN)
        virtual_canvas.blit(lbl, (cx - lbl.get_width() // 2, 210))

        virtual_canvas.blit(font.render("Set Password (optional):", True, WHITE), (cx - 140, 255))
        pass_box = pygame.Rect(cx - 140, 280, 280, 36)
        pygame.draw.rect(virtual_canvas, (25, 30, 45), pass_box, border_radius=4)
        pygame.draw.rect(virtual_canvas, CYAN, pass_box, 2, border_radius=4)
        val_surf = font_large.render(password_input + "|", True, RAINBOW[3])
        virtual_canvas.blit(val_surf, (cx - 130, 288))

        confirm_btn = pygame.Rect(cx - 140, 340, 130, 42)
        cancel_btn = pygame.Rect(cx + 10, 340, 130, 42)
        draw_card(virtual_canvas, confirm_btn, RAINBOW[4] if confirm_btn.collidepoint(mouse_pos) else WHITE)
        draw_card(virtual_canvas, cancel_btn, RAINBOW[1] if cancel_btn.collidepoint(mouse_pos) else WHITE)

        c_txt = font.render("CREATE", True, RAINBOW[4] if confirm_btn.collidepoint(mouse_pos) else WHITE)
        x_txt = font.render("BACK", True, RAINBOW[1] if cancel_btn.collidepoint(mouse_pos) else WHITE)
        virtual_canvas.blit(c_txt, (confirm_btn.centerx - c_txt.get_width() // 2, confirm_btn.centery - 7))
        virtual_canvas.blit(x_txt, (cancel_btn.centerx - x_txt.get_width() // 2, cancel_btn.centery - 7))

        if mouse_click:
            if confirm_btn.collidepoint(mouse_pos) and connect_ws():
                send_msg({"action": "create_room", "public": False, "password": password_input or None})
                menu_mode = "waiting"
                status_message = "Creating private arena..."
            elif cancel_btn.collidepoint(mouse_pos):
                menu_mode = "main"

    elif menu_mode == "join_private":
        card_rect = pygame.Rect(cx - 170, 180, 340, 260)
        draw_card(virtual_canvas, card_rect, CYAN)

        lbl = font_large.render("ENTER PRIVATE LOBBY", True, CYAN)
        virtual_canvas.blit(lbl, (cx - lbl.get_width() // 2, 198))

        c_box = pygame.Rect(cx - 140, 245, 280, 34)
        draw_card(virtual_canvas, c_box, RAINBOW[3] if active_input == "code" else GRAY)
        virtual_canvas.blit(font.render("4-Letter Code:", True, WHITE), (cx - 140, 227))
        virtual_canvas.blit(font_large.render(room_code_input + ("|" if active_input == "code" else ""), True, RAINBOW[3]), (cx - 130, 252))

        p_box = pygame.Rect(cx - 140, 310, 280, 34)
        draw_card(virtual_canvas, p_box, RAINBOW[3] if active_input == "pass" else GRAY)
        virtual_canvas.blit(font.render("Password (if required):", True, WHITE), (cx - 140, 292))
        virtual_canvas.blit(font_large.render(password_input + ("|" if active_input == "pass" else ""), True, RAINBOW[3]), (cx - 130, 317))

        join_btn = pygame.Rect(cx - 140, 365, 130, 42)
        back_btn = pygame.Rect(cx + 10, 365, 130, 42)
        draw_card(virtual_canvas, join_btn, RAINBOW[4] if join_btn.collidepoint(mouse_pos) else WHITE)
        draw_card(virtual_canvas, back_btn, RAINBOW[1] if back_btn.collidepoint(mouse_pos) else WHITE)

        j_txt = font.render("ENTER", True, RAINBOW[4] if join_btn.collidepoint(mouse_pos) else WHITE)
        b_txt = font.render("BACK", True, RAINBOW[1] if back_btn.collidepoint(mouse_pos) else WHITE)
        virtual_canvas.blit(j_txt, (join_btn.centerx - j_txt.get_width() // 2, join_btn.centery - 7))
        virtual_canvas.blit(b_txt, (back_btn.centerx - b_txt.get_width() // 2, back_btn.centery - 7))

        if mouse_click:
            if c_box.collidepoint(mouse_pos):
                active_input = "code"
            elif p_box.collidepoint(mouse_pos):
                active_input = "pass"
            elif join_btn.collidepoint(mouse_pos) and len(room_code_input) == 4 and connect_ws():
                send_msg({"action": "join_room", "room_code": room_code_input, "password": password_input or None})
                status_message = f"Joining room [{room_code_input}]..."
            elif back_btn.collidepoint(mouse_pos):
                menu_mode = "main"

    elif menu_mode == "waiting":
        wait_rect = pygame.Rect(cx - 180, 220, 360, 160)
        draw_card(virtual_canvas, wait_rect, CYAN)

        h_txt = font_large.render(f"ROOM CODE: {room_code}", True, RAINBOW[3])
        virtual_canvas.blit(h_txt, (cx - h_txt.get_width() // 2, 250))

        sub = font.render("Waiting for pilots to connect (Max 6)...", True, WHITE)
        virtual_canvas.blit(sub, (cx - sub.get_width() // 2, 295))

        pulse = int((pygame.time.get_ticks() / 5) % 100)
        pygame.draw.circle(virtual_canvas, CYAN, (cx, 340), 6 + (pulse // 15), 2)

    stat_surf = font.render(status_message, True, status_color)
    virtual_canvas.blit(stat_surf, (cx - stat_surf.get_width() // 2, V_HEIGHT - 50))

    present_frame()
    clock.tick(60)

# --- Gameplay Setup ---
my_color = RAINBOW.get(my_id, RAINBOW[1])
pygame.display.set_caption(f"AstraClash - Pilot {my_id} [Room: {room_code}]")

SHIP_SIZE = 20
BASE_MOVE_SPEED = 5.0
BASE_ROT_SPEED = 4.0
WORLD_BOUND = 3000
ASTEROID_COUNT = 85

def make_ship(p_id):
    col = RAINBOW.get(p_id, RAINBOW[1])
    angle_offset = (p_id - 1) * (360.0 / 6)
    spawn_rad = math.radians(angle_offset)
    return {
        "id": p_id,
        "world_x": 400.0 * math.cos(spawn_rad),
        "world_y": 400.0 * math.sin(spawn_rad),
        "vx": 0.0, "vy": 0.0,
        "angle": (angle_offset + 180.0) % 360.0,
        "color": col,
        "hp": 6, "max_hp": 6,
        "alive": True, "xp": 0, "tier": 0,
        "ore_mana": 0.0, "max_ore_mana": 100.0,
        "autopilot_unlocked": False,
        "autopilot": False,
        "cooldown": 0.0
    }

my_ship = make_ship(my_id)
remote_ships = {}

lasers = []
ores = []
asteroids = []

# Spawn Asteroids with 25% guaranteed Ore Asteroid distribution
def create_asteroid(idx):
    is_ore = (random.random() < 0.25)
    return {
        "id": idx,
        "x": random.uniform(-WORLD_BOUND + 150, WORLD_BOUND - 150),
        "y": random.uniform(-WORLD_BOUND + 150, WORLD_BOUND - 150),
        "vx": random.uniform(-0.8, 0.8),
        "vy": random.uniform(-0.8, 0.8),
        "r": random.randint(26, 48) if is_ore else random.randint(22, 44),
        "hp": 6 if is_ore else 4,
        "max_hp": 6 if is_ore else 4,
        "is_ore": is_ore
    }

if my_id == 1:
    random.seed(42)
    asteroids = [create_asteroid(i) for i in range(ASTEROID_COUNT)]

def spawn_ore_cluster(x, y, count):
    for _ in range(count):
        ores.append({
            "x": x + random.uniform(-16, 16),
            "y": y + random.uniform(-16, 16)
        })

def get_rotated_points(cx, cy, angle, size):
    rad = math.radians(angle)
    tx = cx + size * math.cos(rad)
    ty = cy - size * math.sin(rad)
    lx = cx + (size * 0.75) * math.cos(rad + math.radians(140))
    ly = cy - (size * 0.75) * math.sin(rad + math.radians(140))
    rx = cx + (size * 0.75) * math.cos(rad - math.radians(140))
    ry = cy - (size * 0.75) * math.sin(rad - math.radians(140))
    return [(tx, ty), (lx, ly), (rx, ry)]

def draw_offscreen_marker(surface, cam_x, cam_y, tx, ty, color, w, h):
    dx, dy = tx - cam_x, ty - cam_y
    if dx == 0 and dy == 0:
        return
    pad = 26
    scale_x = ((w // 2) - pad) / abs(dx) if dx != 0 else float("inf")
    scale_y = ((h // 2) - pad) / abs(dy) if dy != 0 else float("inf")
    scale = min(scale_x, scale_y)
    ex = (w // 2) + dx * scale
    ey = (h // 2) + dy * scale
    ang = math.atan2(-dy, dx)
    ms = 11
    p_tip = (ex + ms * math.cos(ang), ey - ms * math.sin(ang))
    p_left = (ex + (ms * 0.8) * math.cos(ang + math.radians(145)), ey - (ms * 0.8) * math.sin(ang + math.radians(145)))
    p_right = (ex + (ms * 0.8) * math.cos(ang - math.radians(145)), ey - (ms * 0.8) * math.sin(ang - math.radians(145)))
    pygame.draw.polygon(surface, color, [p_tip, p_left, p_right])
    pygame.draw.polygon(surface, WHITE, [p_tip, p_left, p_right], 1)

# --- Active Gameplay Loop ---
running = True
while running:
    dt = clock.tick(60) / 1000.0

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.VIDEORESIZE:
            screen = pygame.display.set_mode((event.w, event.h), pygame.RESIZABLE)
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_e:
                if my_ship["autopilot_unlocked"] and my_ship["ore_mana"] > 0:
                    my_ship["autopilot"] = not my_ship["autopilot"]
                else:
                    my_ship["autopilot"] = False
            elif event.key in (pygame.K_1, pygame.K_2):
                needed = (my_ship["tier"] + 1) * 100
                if my_ship["xp"] >= needed and my_ship["tier"] < 5:
                    my_ship["tier"] += 1
                    if event.key == pygame.K_1:
                        my_ship["autopilot_unlocked"] = True
                    my_ship["max_hp"] += 2
                    my_ship["hp"] = min(my_ship["hp"] + 2, my_ship["max_hp"])

    # Receive packets from all peers
    try:
        while True:
            raw = ws.recv()
            if not raw:
                break
            pkt = json.loads(raw)
            action = pkt.get("action")
            if action == "game_packet":
                payload = pkt["payload"]
                p_ship = payload["ship"]
                r_id = p_ship["id"]
                remote_ships[r_id] = p_ship
                if my_id != 1:
                    if "asteroids" in payload:
                        asteroids = payload["asteroids"]
                    if "ores" in payload:
                        ores = payload["ores"]
                for r_laser in payload.get("new_lasers", []):
                    lasers.append(r_laser)
            elif action == "player_left":
                p_left = pkt.get("player_id")
                if p_left in remote_ships:
                    del remote_ships[p_left]
    except (websocket.WebSocketTimeoutException, BlockingIOError):
        pass

    new_local_lasers = []

    # Instant Respawn Logic (No death/respawn screen)
    if my_ship["hp"] <= 0:
        my_ship["hp"] = my_ship["max_hp"]
        my_ship["world_x"] = random.uniform(-1000, 1000)
        my_ship["world_y"] = random.uniform(-1000, 1000)
        my_ship["vx"] = 0.0
        my_ship["vy"] = 0.0
        my_ship["ore_mana"] = max(0.0, my_ship["ore_mana"] - 30.0)
        my_ship["autopilot"] = False

    if my_ship["cooldown"] > 0:
        my_ship["cooldown"] -= dt

    keys = pygame.key.get_pressed()

    # Autopilot Behavior
    if my_ship["autopilot"] and my_ship["autopilot_unlocked"]:
        if my_ship["ore_mana"] > 0:
            my_ship["ore_mana"] = max(0.0, my_ship["ore_mana"] - 14 * dt)
            # Target closest rival
            closest_dist = float("inf")
            target_pos = None
            for p in remote_ships.values():
                d = math.hypot(p["world_x"] - my_ship["world_x"], p["world_y"] - my_ship["world_y"])
                if d < closest_dist:
                    closest_dist = d
                    target_pos = (p["world_x"], p["world_y"])

            if target_pos:
                t_dx = target_pos[0] - my_ship["world_x"]
                t_dy = target_pos[1] - my_ship["world_y"]
                target_ang = math.degrees(math.atan2(-t_dy, t_dx)) % 360
                diff = (target_ang - my_ship["angle"] + 180) % 360 - 180
                my_ship["angle"] += max(-BASE_ROT_SPEED, min(BASE_ROT_SPEED, diff))

                rad = math.radians(my_ship["angle"])
                my_ship["vx"] += 0.3 * math.cos(rad)
                my_ship["vy"] -= 0.3 * math.sin(rad)

                if abs(diff) < 16 and my_ship["cooldown"] <= 0:
                    l_obj = {
                        "x": my_ship["world_x"] + SHIP_SIZE * math.cos(rad),
                        "y": my_ship["world_y"] - SHIP_SIZE * math.sin(rad),
                        "angle": my_ship["angle"],
                        "owner": my_id
                    }
                    lasers.append(l_obj)
                    new_local_lasers.append(l_obj)
                    my_ship["cooldown"] = 0.22
        else:
            my_ship["autopilot"] = False

    # Manual Controls
    if not my_ship["autopilot"]:
        turn = 0
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            turn += 1
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            turn -= 1
        my_ship["angle"] += turn * BASE_ROT_SPEED

        if keys[pygame.K_w] or keys[pygame.K_UP]:
            rad = math.radians(my_ship["angle"])
            my_ship["vx"] += 0.32 * math.cos(rad)
            my_ship["vy"] -= 0.32 * math.sin(rad)

        if (keys[pygame.K_SPACE] or keys[pygame.K_s] or keys[pygame.K_DOWN]) and my_ship["cooldown"] <= 0:
            rad = math.radians(my_ship["angle"])
            l_obj = {
                "x": my_ship["world_x"] + SHIP_SIZE * math.cos(rad),
                "y": my_ship["world_y"] - SHIP_SIZE * math.sin(rad),
                "angle": my_ship["angle"],
                "owner": my_id
            }
            lasers.append(l_obj)
            new_local_lasers.append(l_obj)
            my_ship["cooldown"] = 0.2
            my_ship["world_x"] -= 0.6 * math.cos(rad)
            my_ship["world_y"] += 0.6 * math.sin(rad)

    my_ship["vx"] *= 0.96
    my_ship["vy"] *= 0.96
    my_ship["world_x"] += my_ship["vx"]
    my_ship["world_y"] += my_ship["vy"]

    # 1. Asteroid Hitbox & Elastic Collision (Ship vs Asteroid)
    for a in asteroids:
        dx = my_ship["world_x"] - a["x"]
        dy = my_ship["world_y"] - a["y"]
        dist = math.hypot(dx, dy)
        min_dist = a["r"] + SHIP_SIZE - 2
        if dist < min_dist and dist > 0:
            nx = dx / dist
            ny = dy / dist
            overlap = min_dist - dist
            my_ship["world_x"] += nx * overlap
            my_ship["world_y"] += ny * overlap
            # Elastic bounce impulse
            my_ship["vx"] = nx * 3.5
            my_ship["vy"] = ny * 3.5

    # 1 & 4. Laser Hitbox Collisions (Laser vs Asteroid & Guaranteed Ores)
    for l in lasers[:]:
        r = math.radians(l["angle"])
        l["x"] += 13.0 * math.cos(r)
        l["y"] -= 13.0 * math.sin(r)

        if math.hypot(l["x"] - my_ship["world_x"], l["y"] - my_ship["world_y"]) > 1600:
            lasers.remove(l)
            continue

        hit_ast = False
        for a in asteroids:
            if math.hypot(l["x"] - a["x"], l["y"] - a["y"]) < a["r"]:
                a["hp"] -= 1
                hit_ast = True
                if a["hp"] <= 0:
                    # Guaranteed ore drop from ore asteroids, 12.5% chance from normal ones
                    if a.get("is_ore", False):
                        spawn_ore_cluster(a["x"], a["y"], random.randint(4, 7))
                    elif random.random() < 0.125:
                        spawn_ore_cluster(a["x"], a["y"], random.randint(2, 4))

                    # Continuous asteroid respawning
                    if my_id == 1:
                        new_ast = create_asteroid(a["id"])
                        a.update(new_ast)
                break

        if hit_ast:
            if l in lasers:
                lasers.remove(l)
            continue

        # Laser vs Ship Collisions
        if l["owner"] != my_id:
            if math.hypot(l["x"] - my_ship["world_x"], l["y"] - my_ship["world_y"]) < SHIP_SIZE:
                my_ship["hp"] -= 1
                if l in lasers:
                    lasers.remove(l)

    # Asteroid Drifting
    for a in asteroids:
        a["x"] += a["vx"]
        a["y"] += a["vy"]

    # Ore Magnet & Harvesting
    for o in ores[:]:
        d = math.hypot(o["x"] - my_ship["world_x"], o["y"] - my_ship["world_y"])
        if d < 160:
            o["x"] += (my_ship["world_x"] - o["x"]) * 0.09
            o["y"] += (my_ship["world_y"] - o["y"]) * 0.09
        if d < 24:
            ores.remove(o)
            my_ship["ore_mana"] = min(my_ship["max_ore_mana"], my_ship["ore_mana"] + 20)
            my_ship["xp"] += 25

    # Outgoing Packet Sync
    out_payload = {
        "ship": my_ship,
        "new_lasers": new_local_lasers
    }
    if my_id == 1:
        out_payload["asteroids"] = asteroids
        out_payload["ores"] = ores

    try:
        send_msg({"action": "game_packet", "payload": out_payload})
    except Exception:
        pass

    # --- Draw Arena on Virtual Canvas ---
    cam_x, cam_y = my_ship["world_x"], my_ship["world_y"]
    cx, cy = V_WIDTH // 2, V_HEIGHT // 2
    virtual_canvas.fill(BLACK)

    # 1 & 4. Render Asteroids & Distinct Ore Asteroids
    for a in asteroids:
        ax = a["x"] - cam_x + cx
        ay = a["y"] - cam_y + cy
        if -60 <= ax <= V_WIDTH + 60 and -60 <= ay <= V_HEIGHT + 60:
            is_ore = a.get("is_ore", False)
            base_col = ORE_ASTEROID_COLOR if is_ore else ASTEROID_COLOR
            edge_col = ORE_BLUE if is_ore else (85, 80, 95)

            pygame.draw.circle(virtual_canvas, base_col, (int(ax), int(ay)), a["r"])
            pygame.draw.circle(virtual_canvas, edge_col, (int(ax), int(ay)), a["r"], 2 if not is_ore else 3)

            # Crystal ore core veins for ore asteroids
            if is_ore:
                pygame.draw.circle(virtual_canvas, ORE_BLUE, (int(ax), int(ay)), int(a["r"] * 0.35))
                pygame.draw.circle(virtual_canvas, WHITE, (int(ax), int(ay)), int(a["r"] * 0.15))

            # Hitbox Health Bars
            bar_w = int(a["r"] * 1.5)
            bar_h = 4
            bx = int(ax - bar_w // 2)
            by_pos = int(ay - a["r"] - 10)
            pygame.draw.rect(virtual_canvas, DARK_GRAY, (bx, by_pos, bar_w, bar_h))
            hp_pct = max(0.0, a["hp"] / a.get("max_hp", 4))
            pygame.draw.rect(virtual_canvas, RAINBOW[4], (bx, by_pos, int(bar_w * hp_pct), bar_h))

    # Glowing Blue Ores
    pulse = (pygame.time.get_ticks() // 150) % 3
    for o in ores:
        ox = o["x"] - cam_x + cx
        oy = o["y"] - cam_y + cy
        if -20 <= ox <= V_WIDTH + 20 and -20 <= oy <= V_HEIGHT + 20:
            pygame.draw.circle(virtual_canvas, (0, 100, 180), (int(ox), int(oy)), 6 + pulse, 1)
            pygame.draw.circle(virtual_canvas, ORE_BLUE, (int(ox), int(oy)), 4)
            pygame.draw.circle(virtual_canvas, WHITE, (int(ox), int(oy)), 2)

    # Lasers
    for l in lasers:
        lx = l["x"] - cam_x + cx
        ly = l["y"] - cam_y + cy
        rad = math.radians(l["angle"])
        l_col = RAINBOW.get(l.get("owner", 1), LASER_RED)
        pygame.draw.line(virtual_canvas, l_col, (lx, ly), (lx + 15 * math.cos(rad), ly - 15 * math.sin(rad)), 3)

    # 3. Draw All Remote Rainbow Ships & Offscreen Indicators
    for r_id, p_ship in remote_ships.items():
        if not p_ship.get("alive", True):
            continue
        ox = p_ship["world_x"] - cam_x + cx
        oy = p_ship["world_y"] - cam_y + cy
        r_col = RAINBOW.get(r_id, RAINBOW[2])

        if 0 <= ox <= V_WIDTH and 0 <= oy <= V_HEIGHT:
            pts = get_rotated_points(ox, oy, p_ship["angle"], SHIP_SIZE)
            pygame.draw.polygon(virtual_canvas, r_col, pts, 3)
            # Health Bar
            pygame.draw.rect(virtual_canvas, LASER_RED, (ox - 17, oy - 28, 34, 5))
            pct = max(0.0, p_ship["hp"] / p_ship["max_hp"])
            pygame.draw.rect(virtual_canvas, RAINBOW[4], (ox - 17, oy - 28, int(34 * pct), 5))
        else:
            draw_offscreen_marker(virtual_canvas, cam_x, cam_y, p_ship["world_x"], p_ship["world_y"], r_col, V_WIDTH, V_HEIGHT)

    # Local Ship
    pts = get_rotated_points(cx, cy, my_ship["angle"], SHIP_SIZE)
    pygame.draw.polygon(virtual_canvas, my_color, pts, 3)
    if my_ship["autopilot"]:
        pygame.draw.circle(virtual_canvas, CYAN, (cx, cy), SHIP_SIZE + 6, 1)

    pygame.draw.rect(virtual_canvas, LASER_RED, (cx - 17, cy - 28, 34, 5))
    pct = max(0.0, my_ship["hp"] / my_ship["max_hp"])
    pygame.draw.rect(virtual_canvas, RAINBOW[4], (cx - 17, cy - 28, int(34 * pct), 5))

    # --- Top Status Bar ---
    bm, by, bw, bh = 20, 18, V_WIDTH - 40, 14
    pygame.draw.rect(virtual_canvas, XP_BG, (bm, by, bw, bh), border_radius=4)
    prog = min(1.0, my_ship["xp"] / 530)
    pygame.draw.rect(virtual_canvas, XP_BLUE, (bm, by, int(bw * prog), bh), border_radius=4)
    pygame.draw.rect(virtual_canvas, GRAY, (bm, by, bw, bh), 2, border_radius=4)

    # Ore Mana Gauge
    mana_pct = my_ship["ore_mana"] / my_ship["max_ore_mana"]
    pygame.draw.rect(virtual_canvas, XP_BG, (20, 42, 140, 8), border_radius=2)
    pygame.draw.rect(virtual_canvas, CYAN, (20, 42, int(140 * mana_pct), 8), border_radius=2)

    if not my_ship["autopilot_unlocked"]:
        ap_label = "LOCKED (UPGRADE REQUIRED)"
        ap_col = GRAY
    else:
        ap_label = "ACTIVE" if my_ship["autopilot"] else "STANDBY"
        ap_col = CYAN if my_ship["autopilot"] else WHITE

    ap_text = font.render(f"AUTOPILOT (E): {ap_label}", True, ap_col)
    virtual_canvas.blit(ap_text, (20, 54))

    # Player Badge & Tier Indicator
    p_badge = font.render(f"PILOT {my_id}/6", True, my_color)
    virtual_canvas.blit(p_badge, (V_WIDTH - 245, 42))

    tier_text = font.render(f"TIER {my_ship['tier']}/5  XP: {my_ship['xp']}", True, RAINBOW[3])
    virtual_canvas.blit(tier_text, (V_WIDTH - 150, 42))

    if my_ship["xp"] >= (my_ship["tier"] + 1) * 100 and my_ship["tier"] < 5:
        up_text = font.render("UPGRADE READY: PRESS 1 (AUTOPILOT) OR 2 (SHIELD BOOST)", True, RAINBOW[4])
        virtual_canvas.blit(up_text, (V_WIDTH // 2 - up_text.get_width() // 2, 42))

    present_frame()

if ws:
    ws.close()
pygame.quit()

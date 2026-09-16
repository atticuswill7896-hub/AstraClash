import json
import math
import sys
import pygame
import websocket

# Set this to your actual Render URL (use wss://, not https://)
RENDER_URL = input("Enter Render URL (e.g. wss://astraclash.onrender.com): ").strip()
if not RENDER_URL.startswith("wss://") and not RENDER_URL.startswith("ws://"):
    RENDER_URL = f"wss://{RENDER_URL}"

print("Connecting to cloud server...")
try:
    ws = websocket.create_connection(RENDER_URL, timeout=45)
except Exception as e:
    print(f"Failed to connect to Render server: {e}")
    sys.exit()

def send_msg(payload):
    ws.send(json.dumps(payload))

def recv_msg():
    data = ws.recv()
    return json.loads(data) if data else None

print("\n=== ASTRACLASH MATCHMAKING ===")
print("1. Quick Play (Public Matchmaking)")
print("2. Host Private Room (Password Protected)")
print("3. Join Private Room by Code")
choice = input("Select option (1-3): ").strip()

my_id = 1
room_code = ""

if choice == "1":
    send_msg({"action": "list_public"})
    res = recv_msg()
    rooms = res.get("rooms", []) if res else []
    if not rooms:
        send_msg({"action": "create_room", "public": True, "password": None})
        resp = recv_msg()
        my_id = resp["player_id"]
        room_code = resp["room_code"]
        print(f"Created public room [{room_code}]. Waiting for an opponent...")
        while True:
            ev = recv_msg()
            if ev and ev.get("action") == "player_joined":
                print("Opponent joined! Launching game...")
                break
    else:
        send_msg({"action": "join_room", "room_code": rooms[0], "password": None})
        resp = recv_msg()
        my_id = resp["player_id"]
        room_code = resp["room_code"]
        print(f"Joined public room [{room_code}] as Player 2! Launching game...")

elif choice == "2":
    pwd = input("Set room password: ").strip()
    send_msg({"action": "create_room", "public": False, "password": pwd})
    resp = recv_msg()
    my_id = resp["player_id"]
    room_code = resp["room_code"]
    print(f"\nPrivate Room Created!")
    print(f"Room Code: {room_code}")
    print(f"Password:  {pwd}")
    print("Share these with your friend. Waiting for connection...")
    while True:
        ev = recv_msg()
        if ev and ev.get("action") == "player_joined":
            print("Friend joined! Launching game...")
            break

elif choice == "3":
    code = input("Enter 4-character Room Code: ").strip().upper()
    pwd = input("Enter password (press Enter if none): ").strip() or None
    send_msg({"action": "join_room", "room_code": code, "password": pwd})
    resp = recv_msg()
    if resp.get("status") == "ok":
        my_id = resp["player_id"]
        room_code = resp["room_code"]
        print(f"Joined room [{room_code}]! Launching game...")
    else:
        print(f"Join failed: {resp.get('msg', 'Error')}")
        ws.close()
        sys.exit()

# --- Game Engine Initialization ---
pygame.init()
WIDTH, HEIGHT = 1000, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
pygame.display.set_caption(f"AstraClash - Player {my_id} [Room: {room_code}]")
clock = pygame.time.Clock()

BLACK = (10, 10, 25)
WHITE = (255, 255, 255)
CYAN = (0, 255, 255)
YELLOW = (255, 220, 50)
SHIP_RED = (255, 60, 60)
LASER_RED = (255, 50, 50)
GREEN = (50, 255, 50)
GRAY = (140, 140, 150)
XP_BG = (20, 30, 50)
XP_BLUE = (0, 180, 255)

SHIP_SIZE = 20
BASE_MOVE_SPEED = 5.0
BASE_ROT_SPEED = 4.0

def create_ship(p_id, spawn_x, color, angle):
    return {
        "id": p_id, "world_x": spawn_x, "world_y": 0.0,
        "angle": angle, "color": color, "hp": 6, "max_hp": 6,
        "alive": True, "xp": 0
    }

my_ship = create_ship(my_id, -200.0 if my_id == 1 else 200.0, SHIP_RED if my_id == 1 else YELLOW, 0.0 if my_id == 1 else 180.0)
opp_ship = create_ship(2 if my_id == 1 else 1, 200.0 if my_id == 1 else -200.0, YELLOW if my_id == 1 else SHIP_RED, 180.0 if my_id == 1 else 0.0)

lasers = []

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
    pad = 24
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

ws.settimeout(0.001)

while True:
    dt = clock.tick(60) / 1000.0

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            ws.close()
            pygame.quit()
            sys.exit()
        elif event.type == pygame.VIDEORESIZE:
            WIDTH, HEIGHT = event.w, event.h
            screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
        elif event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_SPACE, pygame.K_s, pygame.K_DOWN):
                rad = math.radians(my_ship["angle"])
                lasers.append({
                    "x": my_ship["world_x"] + SHIP_SIZE * math.cos(rad),
                    "y": my_ship["world_y"] - SHIP_SIZE * math.sin(rad),
                    "angle": my_ship["angle"],
                    "owner": my_id
                })

    # Poll network updates from rival
    try:
        raw = ws.recv()
        if raw:
            data = json.loads(raw)
            if data.get("action") == "game_packet":
                opp_ship.update(data["payload"]["ship"])
                if "lasers" in data["payload"]:
                    lasers = data["payload"]["lasers"]
            elif data.get("action") == "player_left":
                print("Opponent disconnected.")
    except (websocket.WebSocketTimeoutException, BlockingIOError):
        pass

    # Ship controls
    keys = pygame.key.get_pressed()
    turn = 0
    if keys[pygame.K_a] or keys[pygame.K_LEFT]:
        turn += 1
    if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
        turn -= 1
    my_ship["angle"] += turn * BASE_ROT_SPEED

    if keys[pygame.K_w] or keys[pygame.K_UP]:
        r = math.radians(my_ship["angle"])
        my_ship["world_x"] += BASE_MOVE_SPEED * math.cos(r)
        my_ship["world_y"] -= BASE_MOVE_SPEED * math.sin(r)

    # Move lasers
    for l in lasers[:]:
        r = math.radians(l["angle"])
        l["x"] += 12 * math.cos(r)
        l["y"] -= 12 * math.sin(r)
        if math.hypot(l["x"] - my_ship["world_x"], l["y"] - my_ship["world_y"]) > 1200:
            lasers.remove(l)

    # Sync state outward
    try:
        send_msg({
            "action": "game_packet",
            "payload": {"ship": my_ship, "lasers": lasers}
        })
    except Exception:
        pass

    # Draw viewport
    cam_x, cam_y = my_ship["world_x"], my_ship["world_y"]
    cx, cy = WIDTH // 2, HEIGHT // 2
    screen.fill(BLACK)

    # Render lasers
    for l in lasers:
        lx = l["x"] - cam_x + cx
        ly = l["y"] - cam_y + cy
        rad = math.radians(l["angle"])
        pygame.draw.line(screen, LASER_RED, (lx, ly), (lx + 15 * math.cos(rad), ly - 15 * math.sin(rad)), 3)

    # Render rival or offscreen marker
    if opp_ship["alive"]:
        ox = opp_ship["world_x"] - cam_x + cx
        oy = opp_ship["world_y"] - cam_y + cy
        if 0 <= ox <= WIDTH and 0 <= oy <= HEIGHT:
            pts = get_rotated_points(ox, oy, opp_ship["angle"], SHIP_SIZE)
            pygame.draw.polygon(screen, opp_ship["color"], pts, 3)
            pygame.draw.rect(screen, LASER_RED, (ox - 17, oy - 28, 34, 5))
            pygame.draw.rect(screen, GREEN, (ox - 17, oy - 28, 34 * (opp_ship["hp"] / opp_ship["max_hp"]), 5))
        else:
            draw_offscreen_marker(screen, cam_x, cam_y, opp_ship["world_x"], opp_ship["world_y"], opp_ship["color"], WIDTH, HEIGHT)

    # Render local ship
    if my_ship["alive"]:
        pts = get_rotated_points(cx, cy, my_ship["angle"], SHIP_SIZE)
        pygame.draw.polygon(screen, my_ship["color"], pts, 3)
        pygame.draw.rect(screen, LASER_RED, (cx - 17, cy - 28, 34, 5))
        pygame.draw.rect(screen, GREEN, (cx - 17, cy - 28, 34 * (my_ship["hp"] / my_ship["max_hp"]), 5))

    # Top Status Bar
    bm, by, bw, bh = 20, 18, WIDTH - 40, 14
    pygame.draw.rect(screen, XP_BG, (bm, by, bw, bh), border_radius=4)
    prog = min(1.0, my_ship["xp"] / 530)
    pygame.draw.rect(screen, XP_BLUE, (bm, by, int(bw * prog), bh), border_radius=4)
    pygame.draw.rect(screen, GRAY, (bm, by, bw, bh), 2, border_radius=4)

    pygame.display.flip()

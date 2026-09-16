import asyncio
import json
import os
import random
import string
import websockets

PORT = int(os.environ.get("PORT", 8765))
ROOMS = {}

def generate_room_code():
    while True:
        code = "".join(random.choices(string.ascii_uppercase + string.digits, k=4))
        if code not in ROOMS:
            return code

async def handle_client(websocket):
    current_room = None
    player_id = None

    try:
        async for message in websocket:
            msg = json.loads(message)
            action = msg.get("action")

            if action == "create_room":
                is_public = msg.get("public", True)
                password = msg.get("password")
                room_code = generate_room_code()

                ROOMS[room_code] = {
                    "password": password,
                    "is_public": is_public,
                    "clients": [websocket],
                    "players": {1: websocket}
                }
                current_room = room_code
                player_id = 1
                await websocket.send(json.dumps({"status": "ok", "room_code": room_code, "player_id": 1}))

            elif action == "list_public":
                available = [
                    code for code, info in ROOMS.items()
                    if info["is_public"] and len(info["clients"]) < 2
                ]
                await websocket.send(json.dumps({"status": "ok", "rooms": available}))

            elif action == "join_room":
                room_code = msg.get("room_code", "").upper()
                password = msg.get("password")

                if room_code not in ROOMS:
                    await websocket.send(json.dumps({"status": "error", "msg": "Room not found."}))
                    continue

                room = ROOMS[room_code]
                if len(room["clients"]) >= 2:
                    await websocket.send(json.dumps({"status": "error", "msg": "Room is full."}))
                    continue

                if room["password"] is not None and room["password"] != password:
                    await websocket.send(json.dumps({"status": "error", "msg": "Invalid password."}))
                    continue

                room["clients"].append(websocket)
                room["players"][2] = websocket
                current_room = room_code
                player_id = 2

                await websocket.send(json.dumps({"status": "ok", "room_code": room_code, "player_id": 2}))
                await room["players"][1].send(json.dumps({"action": "player_joined", "player_id": 2}))

            elif action == "game_packet":
                if current_room and current_room in ROOMS:
                    room = ROOMS[current_room]
                    for client in room["clients"]:
                        if client != websocket:
                            await client.send(json.dumps(msg))

    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        if current_room and current_room in ROOMS:
            room = ROOMS[current_room]
            if websocket in room["clients"]:
                room["clients"].remove(websocket)
            for peer in room["clients"]:
                try:
                    await peer.send(json.dumps({"action": "player_left"}))
                except Exception:
                    pass
            if not room["clients"]:
                del ROOMS[current_room]

async def main():
    print(f"Server starting on port {PORT}...")
    async with websockets.serve(handle_client, "0.0.0.0", PORT):
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())

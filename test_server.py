#!/usr/bin/env python3
"""Standalone test server for Spyster UI development.

Run with: python test_server.py
Then open: http://localhost:8123/api/spyster/host
"""

import asyncio
import json
import secrets
import time
from pathlib import Path
from aiohttp import web, WSMsgType

# Configuration
HOST = "localhost"
PORT = 8123
WWW_DIR = Path(__file__).parent / "custom_components" / "spyster" / "www"

# Game state simulation
game_state = {
    "session_id": None,
    "phase": "LOBBY",
    "players": [],
    "current_round": 0,
    "round_count": 5,
    "config": {
        "round_duration_minutes": 7,
        "num_rounds": 5,
        "location_pack": "classic"
    },
    "timer": None,
    "host_id": "host",
    "created_at": None,
}

connected_clients = set()


def create_session():
    """Create a new game session."""
    game_state["session_id"] = secrets.token_urlsafe(8)
    game_state["created_at"] = time.time()
    game_state["phase"] = "LOBBY"
    game_state["players"] = []
    game_state["current_round"] = 0
    return game_state["session_id"]


def get_state_for_broadcast():
    """Get current game state for WebSocket broadcast."""
    return {
        "type": "state",
        "session_id": game_state["session_id"],
        "phase": game_state["phase"],
        "players": game_state["players"],
        "player_count": len(game_state["players"]),
        "current_round": game_state["current_round"],
        "round_count": game_state["round_count"],
        "config": game_state["config"],
        "connected_count": len([p for p in game_state["players"] if p.get("connected")]),
        "can_start": len([p for p in game_state["players"] if p.get("connected")]) >= 4,
        "min_players": 4,
        "max_players": 10,
    }


async def broadcast_state():
    """Broadcast state to all connected clients."""
    state = get_state_for_broadcast()
    message = json.dumps(state)
    for ws in list(connected_clients):
        try:
            await ws.send_str(message)
        except Exception:
            connected_clients.discard(ws)


async def handle_host_page(request):
    """Serve the host HTML page."""
    html_path = WWW_DIR / "host.html"
    if html_path.exists():
        # Create session if none exists
        if not game_state["session_id"]:
            create_session()
        return web.FileResponse(html_path)
    return web.Response(text="host.html not found", status=404)


async def handle_player_page(request):
    """Serve the player HTML page."""
    html_path = WWW_DIR / "player.html"
    if html_path.exists():
        return web.FileResponse(html_path)
    return web.Response(text="player.html not found", status=404)


async def handle_static_css(request):
    """Serve CSS files."""
    filename = request.match_info.get("filename", "styles.css")
    css_path = WWW_DIR / "css" / filename
    if css_path.exists():
        return web.FileResponse(css_path, headers={"Content-Type": "text/css"})
    return web.Response(text=f"CSS file {filename} not found", status=404)


async def handle_static_js(request):
    """Serve JS files."""
    filename = request.match_info.get("filename", "host.js")
    js_path = WWW_DIR / "js" / filename
    if js_path.exists():
        return web.FileResponse(js_path, headers={"Content-Type": "application/javascript"})
    return web.Response(text=f"JS file {filename} not found", status=404)


async def handle_qr(request):
    """Generate QR code."""
    try:
        import qrcode
        import io
        import base64

        join_url = f"http://{HOST}:{PORT}/api/spyster/player?session={game_state['session_id']}"
        qr = qrcode.QRCode(version=1, box_size=10, border=4)
        qr.add_data(join_url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")

        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        qr_base64 = base64.b64encode(buffer.getvalue()).decode()

        return web.json_response({
            "qr_code": f"data:image/png;base64,{qr_base64}",
            "join_url": join_url
        })
    except ImportError:
        # Return placeholder if qrcode not installed
        return web.json_response({
            "qr_code": "",
            "join_url": f"http://{HOST}:{PORT}/api/spyster/player?session={game_state['session_id']}",
            "error": "qrcode library not installed"
        })


async def handle_websocket(request):
    """Handle WebSocket connections."""
    ws = web.WebSocketResponse()
    await ws.prepare(request)

    connected_clients.add(ws)
    print(f"[WS] Client connected. Total: {len(connected_clients)}")

    # Send initial state
    await ws.send_str(json.dumps(get_state_for_broadcast()))

    try:
        async for msg in ws:
            if msg.type == WSMsgType.TEXT:
                try:
                    data = json.loads(msg.data)
                    await handle_ws_message(ws, data)
                except json.JSONDecodeError:
                    await ws.send_str(json.dumps({"type": "error", "message": "Invalid JSON"}))
            elif msg.type == WSMsgType.ERROR:
                print(f"[WS] Error: {ws.exception()}")
    finally:
        connected_clients.discard(ws)
        print(f"[WS] Client disconnected. Total: {len(connected_clients)}")

    return ws


async def handle_ws_message(ws, data):
    """Handle incoming WebSocket messages."""
    msg_type = data.get("type")

    if msg_type == "ping":
        await ws.send_str(json.dumps({"type": "pong"}))

    elif msg_type == "join":
        name = data.get("name", f"Player{len(game_state['players']) + 1}")
        player = {
            "name": name,
            "connected": True,
            "is_host": len(game_state["players"]) == 0,
            "disconnect_duration": None
        }
        game_state["players"].append(player)
        print(f"[GAME] Player joined: {name}")
        await broadcast_state()

    elif msg_type == "admin":
        action = data.get("action")
        await handle_admin_action(action, data)

    elif msg_type == "get_state":
        await ws.send_str(json.dumps(get_state_for_broadcast()))


async def handle_admin_action(action, data):
    """Handle admin actions from host."""
    print(f"[ADMIN] Action: {action}")

    if action == "start_game":
        if len([p for p in game_state["players"] if p.get("connected")]) >= 4:
            game_state["phase"] = "ROLES"
            game_state["current_round"] = 1
            print("[GAME] Game started!")
            await broadcast_state()

            # Simulate role display timer
            await asyncio.sleep(2)
            game_state["phase"] = "QUESTIONING"
            await broadcast_state()
        else:
            print("[GAME] Not enough players to start")

    elif action == "skip_to_vote":
        if game_state["phase"] == "QUESTIONING":
            game_state["phase"] = "VOTE"
            await broadcast_state()

    elif action == "pause_game":
        game_state["previous_phase"] = game_state["phase"]
        game_state["phase"] = "PAUSED"
        await broadcast_state()

    elif action == "resume_game":
        if game_state.get("previous_phase"):
            game_state["phase"] = game_state["previous_phase"]
            await broadcast_state()

    elif action == "end_game":
        game_state["phase"] = "END"
        await broadcast_state()

    elif action == "next_round":
        game_state["current_round"] += 1
        if game_state["current_round"] > game_state["round_count"]:
            game_state["phase"] = "END"
        else:
            game_state["phase"] = "ROLES"
            await asyncio.sleep(2)
            game_state["phase"] = "QUESTIONING"
        await broadcast_state()

    elif action == "advance_turn":
        # Just broadcast state - turn advancement is simulated
        await broadcast_state()


async def add_test_players():
    """Add test players for development."""
    await asyncio.sleep(1)  # Wait for server to start

    test_names = ["Alice", "Bob", "Charlie", "Diana"]
    for name in test_names:
        player = {
            "name": name,
            "connected": True,
            "is_host": name == "Alice",
            "disconnect_duration": None
        }
        game_state["players"].append(player)

    print(f"[TEST] Added {len(test_names)} test players")
    await broadcast_state()


def create_app():
    """Create the aiohttp application."""
    app = web.Application()

    # Routes matching Home Assistant integration
    app.router.add_get("/api/spyster/host", handle_host_page)
    app.router.add_get("/api/spyster/player", handle_player_page)
    app.router.add_get("/api/spyster/static/css/{filename}", handle_static_css)
    app.router.add_get("/api/spyster/static/js/{filename}", handle_static_js)
    app.router.add_get("/api/spyster/qr", handle_qr)
    app.router.add_get("/api/spyster/ws", handle_websocket)

    return app


async def main():
    """Run the test server."""
    # Create session
    create_session()

    app = create_app()
    runner = web.AppRunner(app)
    await runner.setup()

    site = web.TCPSite(runner, HOST, PORT)
    await site.start()

    print(f"""
╔════════════════════════════════════════════════════════════════╗
║                    SPYSTER TEST SERVER                         ║
╠════════════════════════════════════════════════════════════════╣
║  Host Page:   http://{HOST}:{PORT}/api/spyster/host              ║
║  Player Page: http://{HOST}:{PORT}/api/spyster/player            ║
║  Session ID:  {game_state['session_id']:<43} ║
╠════════════════════════════════════════════════════════════════╣
║  Press Ctrl+C to stop                                          ║
╚════════════════════════════════════════════════════════════════╝
""")

    # Add test players automatically
    asyncio.create_task(add_test_players())

    # Keep running
    while True:
        await asyncio.sleep(3600)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[SERVER] Shutting down...")

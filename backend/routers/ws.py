import asyncio
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()
logger = logging.getLogger(__name__)


@router.websocket("/ws/status")
async def ws_status(ws: WebSocket):
    await ws.accept()
    state = ws.app.state.state_manager
    queue = state.subscribe()
    try:
        while True:
            try:
                msg = await asyncio.wait_for(queue.get(), timeout=30.0)
                await ws.send_json(msg)
            except asyncio.TimeoutError:
                # Send a heartbeat ping to keep connection alive
                try:
                    await ws.send_json({"event": "ping", "data": {}})
                except Exception:
                    break
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        logger.debug("WS closed: %s", exc)
    finally:
        state.unsubscribe(queue)
        try:
            await ws.close()
        except Exception:
            pass

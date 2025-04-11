import logging
from fastapi import WebSocket
from async_queue import AsyncQueue
import control_flow_commands as cfc
import starlette.websockets as ws

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("chat")

async def loop(response_queue: AsyncQueue, websocket: WebSocket):
    """
    Main loop for sending data from the response queue to the WebSocket client.
    
    Args:
        response_queue (AsyncQueue): Queue containing data to be sent to the WebSocket client.
        websocket (WebSocket): WebSocket connection object.
    """
    while True:
        data = await response_queue.dequeue()

        if data == cfc.CFC_CLIENT_DISCONNECTED:
            break
        else:
            logger.info(f"Sending data: {data}")
            try:
                await websocket.send_text(data)
            except ws.WebSocketDisconnect:
                break
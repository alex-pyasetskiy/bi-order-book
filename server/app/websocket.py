import asyncio
import re
from typing import Annotated

from fastapi import WebSocket, Depends
from starlette.websockets import WebSocketDisconnect

from app.engine import watch_and_send
from app.trading_pairs import TRADING_PAIRS
from app.connection import MANAGER, ConnectionManager


async def order_book_stream(websocket: WebSocket, client_id: str,
                            connection_manager: Annotated[ConnectionManager, Depends(ConnectionManager)]):
    await connection_manager.connect(websocket, client_id)
    try:
        while True:
            data = await websocket.receive_text()
            symbol = re.sub(r'[^a-zA-Z0-9 -]', '', data).upper()
            print(symbol)
            if symbol not in TRADING_PAIRS:
                await websocket.send_json({'error': f'pair {data} not found!'})
            else:
                loop = asyncio.get_event_loop()
                task = loop.create_task(watch_and_send(websocket, symbol))
                await connection_manager.set_task(client_id, task)
    except WebSocketDisconnect:
        connection_manager.disconnect(client_id)

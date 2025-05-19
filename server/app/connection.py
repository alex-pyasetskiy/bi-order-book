import asyncio
import re
from typing import Annotated

from fastapi import WebSocket, Depends, WebSocketDisconnect

from app.connection import ConnectionManager
from app.trading_pairs import TRADING_PAIRS
from app.engine import process_order_book_updates
import logging

log = logging.getLogger(__name__)

async def order_book_stream(
    websocket: WebSocket,
    client_id: str,
    connection_manager: Annotated[ConnectionManager, Depends(ConnectionManager)],
) -> None:
    """
    Handles a WebSocket connection for streaming order book data for a specified trading pair.

    Args:
        websocket: The WebSocket connection object.
        client_id: The unique identifier for the client.
        connection_manager: The ConnectionManager instance for managing connections.
    """
    await connection_manager.connect(websocket, client_id)
    try:
        while True:
            data = await websocket.receive_text()
            symbol = re.sub(r"[^a-zA-Z0-9 -]", "", data).upper()
            log.info(f"Client {client_id} requested order book for symbol: {symbol}")

            if symbol not in TRADING_PAIRS:
                error_message = f"Pair {data} not found!"
                log.warning(f"Client {client_id} requested invalid symbol: {data}")
                await websocket.send_json({"error": error_message})
                continue  # Important: Continue to the next iteration to avoid errors

            try:
                loop = asyncio.get_event_loop()
                task = loop.create_task(
                    process_order_book_updates(symbol)
                )
                connection_manager.set_task(client_id, task)

                async for update in task:
                    await websocket.send_json(
                        {"bids": update._bids, "asks": update._asks}
                    )
            except Exception as e:
                log.error(f"Error processing order book updates for {symbol} for client {client_id}: {e}")
                await websocket.send_json({"error": f"Error fetching order book data: {e}"})
            finally:
                if connection_manager.has_task(client_id):
                  await connection_manager.get_task(client_id) # type: ignore
                connection_manager.disconnect(client_id)

    except WebSocketDisconnect:
        log.info(f"Client {client_id} disconnected.")
        connection_manager.disconnect(client_id)
    except Exception as e:
        log.error(f"Unexpected error in order_book_stream for client {client_id}: {e}")
        connection_manager.disconnect(client_id)
        await websocket.send_json({"error": f"Internal server error: {e}"})

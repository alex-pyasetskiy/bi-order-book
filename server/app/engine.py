import asyncio
import json
import logging
import socket
from decimal import Decimal
from typing import AsyncIterator, Iterator, List, NamedTuple, Sequence

import aiohttp
from sortedcontainers import SortedDict
from websockets import connect
from websockets.exceptions import ConnectionClosed, ConnectionClosedError
from fastapi import WebSocket

log = logging.getLogger(__name__)


class StreamIntegrityError(Exception):
    """Raised when the order book stream has gaps or inconsistencies."""

    pass


class Offer(NamedTuple):
    """Represents a single offer (price and quantity) in the order book."""

    price: Decimal
    quantity: Decimal


class OrderBookUpdate:
    """Represents an update to the order book with bids and asks."""

    def __init__(self, bids: List[List[str]], asks: List[List[str]], event: dict):
        """
        Initializes an OrderBookUpdate.

        Args:
            bids: A list of bid offers as strings (price, quantity).
            asks: A list of ask offers as strings (price, quantity).
            event: The raw event data.
        """
        self._bids = bids
        self._asks = asks
        self.event = event

    @staticmethod
    def _decode_offers(str_offers: List[List[str]]) -> Iterator[Offer]:
        """Decodes string-based offers into Offer NamedTuples."""
        for str_price, str_quantity in str_offers:
            yield Offer(Decimal(str_price), Decimal(str_quantity))

    @property
    def asks(self) -> Iterator[Offer]:
        """Returns an iterator of ask offers as Decimal types."""
        return self._decode_offers(self._asks)

    @property
    def bids(self) -> Iterator[Offer]:
        """Returns an iterator of bid offers as Decimal types."""
        return self._decode_offers(self._bids)


class OrderBook:
    """Represents the current state of the order book."""

    def __init__(self):
        """Initializes an empty OrderBook with sorted dictionaries for bids and asks."""
        self._bids: SortedDict[Decimal, Decimal] = SortedDict()
        self._asks: SortedDict[Decimal, Decimal] = SortedDict()

    def _update_offers(self, offers_dict: SortedDict[Decimal, Decimal], updates: Sequence[Offer]):
        """Updates the bid or ask dictionary based on a sequence of Offer updates."""
        for update in updates:
            if update.quantity == 0:
                try:
                    del offers_dict[update.price]
                except KeyError:
                    pass  # It's fine if the price wasn't there to begin with
            else:
                offers_dict[update.price] = update.quantity

    def update(self, bids: Sequence[Offer], asks: Sequence[Offer]):
        """Applies updates to both bids and asks in the order book."""
        self._update_offers(self._bids, bids)
        self._update_offers(self._asks, asks)

    @property
    def top_bids(self) -> List[str]:
        """Returns a list of the top 20 bid quantities as strings (highest bids)."""
        return [str(quantity) for quantity in self._bids.values()[-1:-21:-1]]

    @property
    def top_asks(self) -> List[str]:
        """Returns a list of the top 20 ask quantities as strings (lowest asks)."""
        return [str(quantity) for quantity in self._asks.values()[:20]]



class DepthUpdateEvent:
    """Represents a raw depth update event received from the exchange."""

    def __init__(self, event: dict):
        """Initializes a DepthUpdateEvent with the raw event data."""
        self._event = event

    @property
    def raw_event(self) -> dict:
        """Returns the raw event dictionary."""
        return self._event

    @property
    def first_update_id(self) -> int:
        """Returns the first update ID of this event."""
        return self._event.get('U')

    @property
    def last_update_id(self) -> int:
        """Returns the last update ID of this event."""
        return self._event.get('u')

    @property
    def bids(self) -> List[List[str]]:
        """Returns the bid updates as a list of string pairs (price, quantity)."""
        return self._event.get('b', [])

    @property
    def asks(self) -> List[List[str]]:
        """Returns the ask updates as a list of string pairs (price, quantity)."""
        return self._event.get('a', [])


async def fetch_initial_order_book(symbol: str) -> dict:
    """Fetches the initial order book snapshot from the Binance API."""
    http_uri = f'https://api.binance.com/api/v3/depth?symbol={symbol}&limit=20'
    log.info("Fetching initial order book: %s", http_uri)
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as http_session:
        async with http_session.get(http_uri) as http_response:
            http_response.raise_for_status()  # Raise an exception for bad status codes
            return await http_response.json()


async def watch_depth_stream(websocket) -> AsyncIterator[DepthUpdateEvent]:
    """Asynchronously listens to the WebSocket and yields DepthUpdateEvents."""
    async for raw_msg in websocket:
        try:
            msg = json.loads(raw_msg)
            if msg.get('e') == "depthUpdate":
                yield DepthUpdateEvent(msg)
            else:
                log.debug('Skipping non-depthUpdate message: %s', msg.get('e'))
        except json.JSONDecodeError:
            log.warning('Received invalid JSON: %s', raw_msg)
        except Exception as exc:
            log.exception('Error processing WebSocket message: %s', exc)



async def process_order_book_updates(symbol: str) -> AsyncIterator[OrderBookUpdate]:
    """
    Connects to the Binance WebSocket, fetches the initial order book,
    and then processes incoming depth updates, yielding OrderBookUpdate objects.

    Ensures stream integrity by checking update IDs.
    """
    ws_uri = f'wss://stream.binance.com:9443/ws/{symbol.lower()}@depth'
    log.info("Connecting to WebSocket: %s", ws_uri)
    async with connect(ws_uri, ping_interval=1, ping_timeout=5, close_timeout=5) as stream:
        initial_book = await fetch_initial_order_book(symbol)
        order_book_update_id = initial_book['lastUpdateId']
        yield OrderBookUpdate(bids=initial_book['bids'], asks=initial_book['asks'], event=initial_book)
        log.info("Initial order book received (lastUpdateId: %s)", order_book_update_id)

        previous_last_update_id = order_book_update_id

        async for event in watch_depth_stream(stream):
            current_first_update_id = event.first_update_id
            current_last_update_id = event.last_update_id

            if current_last_update_id <= order_book_update_id:
                log.debug("Ignoring outdated event (lastUpdateId: %s <= %s)", current_last_update_id, order_book_update_id)
                continue

            if previous_last_update_id is not None:
                if current_first_update_id != previous_last_update_id + 1:
                    raise StreamIntegrityError(
                        f"Gap in stream detected: expected firstUpdateId {previous_last_update_id + 1}, "
                        f"got {current_first_update_id}"
                    )
            elif not (current_first_update_id <= order_book_update_id + 1 <= current_last_update_id):
                raise StreamIntegrityError(
                    f"Initial stream continuity error: firstUpdateId={current_first_update_id}, "
                    f"lastUpdateId={current_last_update_id}, initialLastUpdateId={order_book_update_id}"
                )

            yield OrderBookUpdate(bids=event.bids, asks=event.asks, event=event.raw_event)
            previous_last_update_id = current_last_update_id


async def handle_websocket_connection(websocket: WebSocket, symbol: str = 'BTCUSDC'):
    """
    Manages a single WebSocket connection, processes order book updates for a given symbol,
    and sends the updates to the connected client.
    """
    await websocket.accept()
    log.info(f"WebSocket connection established for symbol: {symbol}")
    try:
        async for update in process_order_book_updates(symbol):
            await websocket.send_text(json.dumps({'bids': update._bids, 'asks': update._asks}))
    except (ConnectionClosedError, ConnectionClosed, socket.error, asyncio.TimeoutError, StreamIntegrityError) as e:
        log.error(f"WebSocket connection error for {symbol}: {e}")
    finally:
        await websocket.close()
        log.info(f"WebSocket connection closed for symbol: {symbol}")

import logging
import asyncio
from fastapi import WebSocket
import json
import socket
from decimal import Decimal
from typing import Sequence, NamedTuple, List, Iterator
import aiohttp
from sortedcontainers import SortedDict
from websockets import connect
from websockets.exceptions import ConnectionClosedError, ConnectionClosed

log = logging.getLogger(__name__)


class StreamIntegrityError(Exception):
    pass


class Offer(NamedTuple):

    price: Decimal
    quantity: Decimal


class OrderBookUpdate():

    def __init__(self, bids, asks, event):
        self._bids = bids
        self._asks = asks
        self.event = event

    @staticmethod
    def _decode(str_offers):
        for str_price, str_quantity in str_offers:
            yield Offer(Decimal(str_price), Decimal(str_quantity))

    @property
    def asks(self):
        return self._decode(self._asks)

    @property
    def bids(self):
        return self._decode(self._bids)


class OrderBook():

    def __init__(self):
        self._bids = SortedDict()
        self._asks = SortedDict()

    @staticmethod
    def _update(offers_dict, updates: Sequence[Offer]):
        for update in updates:
            if update.quantity == 0:
                try:
                    del offers_dict[update.price]
                except KeyError:
                    pass
            else:
                offers_dict[update.price] = update.quantity

    def update(self, bids: Sequence[Offer], asks: Sequence[Offer]):
        self._update(self._bids, bids)
        self._update(self._asks, asks)

    @property
    def top_bids(self):
        return [str(i) for i in self._bids.values()[-1:-20]]

    @property
    def top_asks(self):
        return [str(i) for i in self._asks.values()[:20]]



class DepthUpdateEvent:

    def __init__(self, event):
        self._event = event

    @property
    def raw_event(self) -> dict:
        return self._event
    @property
    def first_update(self) -> int:
        return self._event['U']

    @property
    def last_update(self) -> int:
        return self._event['u']

    @property
    def bids(self) -> List[str]:
        return self._event['b']

    @property
    def asks(self) -> List[str]:
        return self._event['a']


async def fetch_order_book(symbol):
    http_uri = f'https://api.binance.com/api/v3/depth?symbol={symbol}&limit=20'
    log.info("Getting order book: %r", http_uri)
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as http_session:
        async with http_session.get(http_uri) as http_response:
            return await http_response.json()


async def watch_ws(websocket) -> Iterator[DepthUpdateEvent]:
    while True:
        try:
            recv = await websocket.recv()
            msg = json.loads(recv)

            msg_type = msg.get('e')
            if msg_type == "depthUpdate":
                yield DepthUpdateEvent(msg)
            else:
                log.debug('Message is not depthUpdate. Skipping message, type: %s', msg_type)
        except (ConnectionClosedError, ConnectionClosed) as exc:
            log.exception(exc)
            await websocket.close()


async def watch(symbol):
    """
    - Drop any event where last_update is <= lastUpdateId in the snapshot.
    -  The first processed event should have first_update <= order_book_update_id+1
       AND last_update >= order_book_update_id+1.
    -  While listening to the stream, each new event's first_update should be equal to the previous
       event's last_update.
    """
    ws_uri = f'wss://stream.binance.com:9443/ws/{symbol.lower()}@depth'
    log.info("Listening to: %r", ws_uri)
    async with connect(ws_uri, ping_interval=1, ping_timeout=5, close_timeout=5) as stream:
        order_book_snapshot = await fetch_order_book(symbol)
        yield OrderBookUpdate(bids=order_book_snapshot['bids'], asks=order_book_snapshot['asks'], event=order_book_snapshot)

        order_book_update_id = order_book_snapshot['lastUpdateId']
        log.info("Got order book (update id %r)", order_book_update_id)

        prev_last_update = None
        async for ev in watch_ws(stream):
            if ev.last_update <= order_book_update_id:
                log.info("Ignoring pre-snapshot event: last_update=%r", ev.last_update)
                continue

            if prev_last_update is None:

                if not (ev.first_update <= order_book_update_id + 1 <= ev.last_update):
                    raise StreamIntegrityError(
                        f"Bad continuity starting stream: {ev.first_update=} {ev.last_update=} "
                        "{order_book_update_id=}")
            else:

                if ev.first_update != prev_last_update + 1:
                    raise StreamIntegrityError(
                        f"Update continuity error: {ev.first_update=} != {prev_last_update=}")
            yield OrderBookUpdate(bids=ev.bids, asks=ev.asks, event=ev.raw_event)
            prev_last_update = ev.last_update


async def watch_and_send(websocket: WebSocket, symbol: str = 'BTCUSDC'):
    while True:
        try:
            book = OrderBook()
            async for update in watch(symbol):
                book.update(bids=update.bids, asks=update.asks)

                await websocket.send_json(json.dumps({'bids': update._bids, 'asks': update._asks}))

        except (ConnectionClosedError, socket.error, asyncio.TimeoutError):
            # Start from scratch - this will re-request the order book snapshot, since the stream
            # has been lost.
            log.exception('Connection lost - retrying')
            await asyncio.sleep(5)

import uuid

from fastapi import WebSocket


class ConnectionManager:
    def __new__(cls):
        if not hasattr(cls, 'instance'):
            setattr(cls, '__instance', super(ConnectionManager, cls).__new__(cls))
            # cls.__instance = super(ConnectionManager, cls).__new__(cls)
        return getattr(cls, '__instance')

    def __init__(self):
        self.connections = {}

    def register_client(self) -> uuid.UUID:
        client_id = uuid.uuid4()
        self.connections.update({client_id: {'ws': None, 'task': None}})
        return client_id

    async def connect(self, websocket: WebSocket, client_id):
        await websocket.accept()
        self.connections.update({client_id: { 'ws': websocket, 'task': None}})

    async def set_task(self, client_id, task):
        self.connections[client_id]['task'] = task

    def disconnect(self, client_id: str):
        ws = self.connections.get(client_id)['ws']
        ws.close()



MANAGER = ConnectionManager()
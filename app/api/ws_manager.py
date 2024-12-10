from fastapi import WebSocket
from app.core.logging import logger
from typing import Any

class WSConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        logger.info(f'Websocket accepted: session_id={client_id}')
        exist: WebSocket = self.active_connections.get(client_id)
        if exist:
            await exist.close()  # you want to disconnect connected client.
            self.active_connections[client_id] = websocket
            # await websocket.close()  # reject new user with the same ID already exist
        else:
            self.active_connections[client_id] = websocket

    def disconnect(self, client_id: str):
        self.active_connections.pop(client_id)
        logger.info(f'Websocket closed: session_id={client_id}')

    @staticmethod
    async def send_personal_message(websocket: WebSocket, message: dict[str, any]):
        await websocket.send_json(message)

    async def broadcast(self, message: dict[str, Any]):
        for connection in self.active_connections.values():
            await connection.send_json(message)


ws_manager = WSConnectionManager()
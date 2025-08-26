from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from jose import JWTError, jwt
from typing import Dict, List

app = FastAPI()


SECRET_KEY = "abdul"
ALGORITHM = "HS256"


# Карта для хранения подключений 
connected_clients: Dict[str, List[WebSocket]] = {}

# Верификация JWT токена
def check_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise JWTError()
        return username
    except JWTError:
        return None

# WebSocket для подключения к беседе
@app.websocket("/ws/{chat_name}")
async def websocket_endpoint(websocket: WebSocket, chat_name: str, token: str = Query(...)):
    user = check_token(token)
    if user is None:
        await websocket.close(code=1008)
        return

    await websocket.accept()

    if chat_name not in connected_clients:
        connected_clients[chat_name] = []

    connected_clients[chat_name].append(websocket)

    try:
        for client in connected_clients[chat_name]:
            if client != websocket:
                await client.send_text(f"{user} присоединился.")
        while True:
            data = await websocket.receive_text()
            for client in connected_clients[chat_name]:
                await client.send_text(f"{user}: {data}")
    except WebSocketDisconnect:
        connected_clients[chat_name].remove(websocket)
        for client in connected_clients[chat_name]:
            await client.send_text(f"{user} покинул беседу.")
        if not connected_clients[chat_name]:
            del connected_clients[chat_name]

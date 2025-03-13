import asyncio
import websockets
import aiohttp
import json

async def test_translation():
    # Подключаемся к WebSocket
    async with websockets.connect('ws://localhost:8000/ws') as websocket:
        print("Connected to WebSocket")
        
        # Получаем session_id
        response = await websocket.recv()
        data = json.loads(response)
        if data['type'] == 'connection_established':
            session_id = data['session_id']
            print(f"Received session ID: {session_id}")
        else:
            print("Failed to get session ID")
            return

        # Отправляем запрос на перевод
        async with aiohttp.ClientSession() as session:
            async with session.post('http://localhost:8000/translate', json={
                'text': 'Hello, world!',
                'translator_type': 'yandex',
                'ws_session_id': session_id
            }) as response:
                result = await response.json()
                print(f"Translation request response: {result}")

        # Получаем результат перевода через WebSocket
        result = await websocket.recv()
        print(f"Received translation result: {result}")

if __name__ == "__main__":
    asyncio.run(test_translation())
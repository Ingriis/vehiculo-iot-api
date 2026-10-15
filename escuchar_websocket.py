import asyncio
import os

from dotenv import load_dotenv
import websockets


async def main():
    url = "ws://127.0.0.1:8000/ws/vehicles/1"
    load_dotenv()
    api_key = os.getenv("API_KEY")
    if not api_key:
        raise RuntimeError("Configura API_KEY en .env antes de iniciar la conexión.")

    try:
        async with websockets.connect(
            url, additional_headers={"X-API-Key": api_key}
        ) as ws:
            print("Conexión WebSocket establecida.")
            print("Estado inicial:", await ws.recv())
            print("Escuchando eventos. Presiona Ctrl+C para salir.\n")

            while True:
                mensaje = await ws.recv()
                print("Evento recibido:", mensaje)

    except KeyboardInterrupt:
        print("Prueba finalizada.")
    except Exception as e:
        print("Error de conexión:", e)


asyncio.run(main())

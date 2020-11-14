import asyncio
import websockets

URL = "ws://echo.websocket.org"
#URL = "wss://*********.ngrok.io/ws/"

async def hello():
    async with websockets.connect(URL) as websocket:
    
        data = "serial:1234567890"
        while True:
            await websocket.send(data)
            response = await websocket.recv()
            print(f"response: {response}")
            if response == data:
                break
            await asyncio.sleep(10)
        print("Device Authenicated")
        while True:
            response = await websocket.recv()
            print(f"response: {response}")
            response = response.split(":")
            if "107" in response:
                print("replying query")
                await websocket.send("107:1,1,0,2")
            elif "101" in response:
                print("turn off cmd")
            elif "100" in response:
                print("turn on cmd")
            else:
                print(response)
                
asyncio.get_event_loop().run_until_complete(hello())

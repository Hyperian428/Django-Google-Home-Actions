import os
from channels.generic.websocket import AsyncJsonWebsocketConsumer
#import redis
#import myapp.models
from myapp.models import account

#commands opcode, needs to match the ones in device
deviceOn       = "100"
deviceOff      = "101"
deviceGetSpeed = "102"
deviceSetSpeed = "103"
deviceGetDust  = "104"
deviceAutoOn   = "105"
deviceAutoOff  = "106"
deviceQuery    = "107"

class backEndConsumer(AsyncJsonWebsocketConsumer):

    async def websocket_connect(self, type):
        #self.channel_name = await self.channel_layer.new_channel()
        #await self.channel_layer.group_add("link", self.channel_name)
        # can't do this here if i have to do it after device registration
        await self.accept()

    async def websocket_disconnect(self, close_code = 200):
        # piggybacking self.channel_name to track which account got disconnected
        # to set device status (faster response to google when ask for device that isn't there)
        print("Channel name: "+self.channel_name)
        userDB = None
        try:
            userDB = account.objects.get(backEndChannelName=self.channel_name)
        except:
            print("DISC: cannot find channel_name")
            await self.close(close_code)
            return
        print("Closing channel: " + userDB.backEndChannelName)

        userDB.websocketStatus = False
        userDB.save()

        await self.close(close_code)
        await super().websocket_disconnect({"code": 200})

    # Used for establish connection and also callback from device
    async def websocket_receive(self, text_data=None, bytes_data=None):
        if not text_data:  # this probably should never trigger
            msg = "No text data found"
            #print(msg)
            await self.send(msg)
            self.websocket_disconnect(close_code=4124)
            return
        #print(text_data)
        message = text_data["text"]
        
        if ':' not in message or message[-1] == ':':
            print("invalid message format: " + message)
            return
        lstmsg = message.split(":")
        cmd, data = lstmsg
        # handler for serial number for device registration
        userDB = None
        if cmd == "serial":            
            if len(data) == 10:
                try:
                    userDB = account.objects.get(UID=data)
                except:
                    msg = "SN not found in database"
                    #print(msg)
                    await self.send(msg)
                    await self.websocket_disconnect(close_code=4124)
                    return
                print("SN found in database")
                
                # return serial number to device to allow commands to device
                await self.send("serial:"+data)

                # establish channelname for this account
                userDB.backEndChannelName = self.channel_name
                userDB.websocketStatus = True
                userDB.save()
            else:
                print("No serial Number. Found string: " + str(text_data))
                await self.send("serial:wrong") # no point other than debugging on device end
                self.websocket_disconnect(close_code=4123)
            return
            
        # if device is returning info, need to find out which device it is
        userDB = await self.get_account(4124)
        frontEndChannelName = userDB.frontEndChannelName
        if cmd == deviceGetSpeed: # callback from device for get speed level
            await self.channel_layer.send(frontEndChannelName,
                {
                "type": "speed.callback",
                "where": "websocket",
                "message": data,
                })
        elif cmd == deviceGetDust: # callback from device for get dust level
            await self.channel_layer.send(frontEndChannelName,
                {
                "type": "dust.callback",
                "where": "websocket",
                "message": data,
                })
        elif cmd == deviceQuery:
            await self.channel_layer.send(frontEndChannelName,
                {
                "type": "query.callback",
                "where": "websocket",
                "message": data,
                })
    
#channel layer functions 
    async def websocket_test(self, event):
        print("WS: message from " + event["where"] + ": " + event["message"])
        await self.send(event["message"])

# when query comes through, we need to get 4 points of information from device    
    async def device_query(self, event): # update all states
        #print("WS: querying device")
        userDB = account.objects.get(backEndChannelName=self.channel_name)
        #print("frontendname: " + userDB.frontEndChannelName)
        await self.send(deviceQuery)

    async def device_on(self, event):  # should be make sure device actually got the command
        print("WS: turning device on")
        
        await self.send(deviceOn)
    
    async def device_off(self, event):
        print("WS: turning device off")
        
        await self.send(deviceOff)
        
    async def device_autoOn(self, event):    
        print("WS: set device auto speed On")
        await self.send(deviceAutoOn)

    async def device_autoOff(self, event):
        print("WS: set device auto speed Off")
        await self.send(deviceAutoOff)

    async def device_getSpeed(self, event):
        print("WS: get device speed")
        await self.send(deviceGetSpeed)            
    
    async def device_setSpeed(self, event):
        print("WS: set device speed to: " + event["message"])
        await self.send(deviceSetSpeed + event["message"])
    
    async def device_getDust(self, event):
        print("WS: get device dust")
        await self.send(deviceGetDust)
        # lines below are for loopback testing without actual device
                
    async def get_account(self, errorCode):
        userDB = None
        try:
            userDB = account.objects.get(backEndChannelName=self.channel_name)
        except:
            print("ERR: Cannot locate account information for getSpeed cmd")
            await self.close(close_code)
            self.websocket_disconnect(close_code=errorCode)
            return
        return userDB
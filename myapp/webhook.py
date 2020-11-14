import os
from channels.generic.http import AsyncHttpConsumer
from channels.layers import get_channel_layer
#from django.http import JsonResponse
import json
import random

import myapp.intents
# for setting defines
from django.conf import settings
# for async authorization
import asyncio
from aiohttp import ClientSession
# sqlite3 access
from myapp.models import account
import myapp.models

# trafficTest will only trigger with requestId lower than 100000
# both webhook.py and consumer.py need to have trafficTest on
fakeAccounts = 1000
base = 1000000000

class frontEndConsumer(AsyncHttpConsumer):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # needed for query callback
        # but google doesn't seem to care if i don't send it.
        self.requestId = ""
    
    async def error_reply(self, requestId, error="authFailure"):
        response = myapp.intents.error_intent
        response["requestId"] = requestId
        response["payload"]["errorCode"] = error
        response = json.dumps(response).encode('utf-8')
        print(response)
        await self.send_response(200, response, 
            headers=[(b'Content-Type', b'application/json'),(b'Google-Assistant-API-Version', b'v2')])        

    async def intent_reply(self, response):
        response = response
        await self.send_response(200, response, 
            headers=[(b'Content-Type', b'application/json'),(b'Google-Assistant-API-Version', b'v2')])

    async def test_reply(self, msg):
        msg = {'msg': msg}
        msg = json.dumps(msg).encode('utf-8') 
        await self.send_response(200, msg, 
            headers=[(b"Content-Type", b"application/json; charset=UTF-8"),])      

    async def http_request(self, request):
        body = request.get('body')
        try:                                 # need a catch in case incoming webhook is invalid
            body = json.loads(body.decode()) # decode changes body from byte to string, and changes string to json object
        except:
            print("invalid webhook message")
            await self.error_reply("0")
            return

        requestId = body.get("requestId")
        
        userDB = await self.get_account()
        
        if userDB is None:
            await self.error_reply(requestId)
            return
        
        # changes every time
        userDB.frontEndChannelName = self.channel_name

        # agentUserId checking
        agentUserId = None
        if userDB.intentAgentUserId == "0": # new user
            agentUserId = random.randint(0, 100000)
            # todo: check if new ID is same as other users
            print("new agentUserId: " + str(agentUserId))
            userDB.intentAgentUserId = agentUserId
        else:
            agentUserId = userDB.intentAgentUserId
            #print("found agentUserId: " + str(agentUserId))
        userDB.save()
        
        # get UID from database
        UID = None
        if userDB.UID == None:
            # return error
            print("err: User does not own a device")
            await self.error_reply(requestId)
            return
        else:
            UID = userDB.UID
            #print("found UID: " + UID)
        
        # check if device is active
        if userDB.websocketStatus == False:
            print("err: device not active")
            await self.error_reply(requestId, "authFailure")
            return
        
        intent = body.get("inputs")[0].get("intent")
        #print("Intent: " + intent + ". reqId: " + requestId)
        # decide what to do with each intent
        if intent == "action.devices.SYNC":
            # return the sync response format
            response = myapp.intents.sync_intent
            response["requestId"] = requestId
            response["payload"]["agentUserId"] = agentUserId
            response["payload"]["devices"][0]["id"] = UID
            response = json.dumps(response).encode('utf-8')
            await self.intent_reply(response)
            return
        elif intent == "action.devices.QUERY":
            # keep connection alive at this point, do not close connection
            # it needs to reply via query_callback()
            self.requestId = requestId
            try:
                await self.channel_layer.send(userDB.backEndChannelName,{"type": "device.query"})
            except:
                print("CAUGHT THE ERROR")
                self.channel_layer = get_channel_layer() # get a new channel layer since the old one expired
                # need to get channel name from channel layer?
                await self.channel_layer.send(userDB.backEndChannelName,{"type": "device.query"})
                
        elif intent == "action.devices.EXECUTE":
            # get UID
            UID = await self.get_exec_uid(body)
            if UID == None: 
                print("ERR: action.devices.EXECUTE has no UID")
                await self.error_reply(requestId, error="unableToLocateDevice")
                return
                
            # get command
            command = await self.get_exec_cmd(body)
            if command == None:
                print("ERR: action.devices.EXECUTE has no CMD")
                await self.error_reply(requestId, error="commandInsertFailed")
                return

            #Get action
            param = await self.get_exec_param(body)
            if param == None:
                print("ERR: action.devices.EXECUTE has no param")
                await self.error_reply(requestId, error="notSupported")
                return
            
            #print("command is " + command + " to turn " + param)
            # talk to backend
            await self.send_cmd_backend(body, param, userDB.backEndChannelName)
            
            # generate response for google
            response = await self.create_exec_response(requestId, body, param)
            response = json.dumps(response).encode('utf-8')
            #print(response)
            await self.intent_reply(response)
            await super().http_disconnect("")
            
        elif intent == "action.devices.DISCONNECT":
            print("User disconnected device from Home Control")
            # should disable query and exec commands if user were to send them, but that should never happen
            await super().http_disconnect("")
        else: 
            print("ERR: wrong device command")
            await self.error_reply(requestId, error="unlockFailure")
            await super().http_disconnect("")
        return
        
    async def query_callback(self, event):
        #print("WH: query callback: " + event["message"])
        
        # process the message by dividing it up
        onOff, speed, auto, dust = event["message"].split(",")
        #print("WH: Query callback: onOff: " + onOff + " speed: " + speed + " auto: " + auto + " dust: " + dust)
        userDB = account.objects.get(frontEndChannelName=self.channel_name)
        #print("WH: request ID: " + self.requestId)
        
        # grab the query intent dictionary and populate it with data from device
        response = myapp.intents.query_intent
        response["requestId"] = self.requestId
        # onoff trait
        deviceOnOff = True if onOff == '1' else False
        onOff = {"on": deviceOnOff, "online": True}
        # toggle trait (auto)
        deviceAuto = True if auto == '1' else False
        toggle = {"currentToggleSettings": {"automatic": deviceAuto}}
        # fanspeed trait
        deviceSpeed = int(speed)
        speed = {"currentFanSpeedSetting": deviceSpeed}
        # sensorState trait
        deviceDust = "healthy" if dust == "healthy" else "moderate"
        sensor = {"currentSensorStateData":[{"name": "AirQuality", "currentSensorState": deviceDust}]}
        # general status message required
        status = {"status": "SUCCESS"}
        
        # all of them needs to be in a dict for google to process it
        dicts = {}
        for dict in (onOff, toggle, speed, sensor, status):
            dicts.update(dict)
        response["payload"]["devices"] = {userDB.UID: dicts}
        response = json.dumps(response).encode('utf-8')
        
        # need something to close the redis channel, otherwise when redis connection times out, it will cause an error on the next cmd.
        await self.intent_reply(response)
        # does not seem to fix the redis connection issue
        await super().http_disconnect("")

    async def webhook_test(self, event):
        print("WH: message from " + event["where"] + ": " + event["message"])

# Uses either bearer or email to find account, if bearer is outdated, then use new bearer to grab email,
# then update bearer, this is to be nice to the auth server (cause it's free)
    async def get_account(self):
        # use identifying information to get user data in internal database
        bearer = ""
        try:
            headers = self.scope.get('headers')
        except:
            print("err: Wrong header format (no header)")
            print(self.scope)
            return None
        # the bearer does not come in order, have to find it.
        for piece in headers:
            if b'authorization' in piece[0]:
                bearer = piece[1].decode('utf-8')
                #print("found bearer " + bearer)
                break

        auth = {'authorization': bearer}
        userDB = None
        try:
            userDB = account.objects.get(accessToken=bearer)
        except:
            print("No bearer match, using auth0")
            domain = settings.SOCIAL_AUTH_AUTH0_DOMAIN
            url = "https://" + domain + "/userinfo"
            print("auth")
            print(auth)
            async with ClientSession() as session:
                async with session.request("GET", url, headers=auth) as response:
                    response = await response.read()
            # bad request response could happen here if you don't white list your URL in auth0
            print(response)
            response = response.decode('utf-8') # byte array -> string
            response = json.loads(response) # string -> json
            email = response.get("email")
            if email is None:
                # if email is none, then probably got throttled, just error for now
                userDB = None
            else: # found email
                userDB = account.objects.get(email=email)
                # update bearer
                userDB.accessToken = bearer
                userDB.save()
        #else:
        #   print("bearer match records")
        return userDB
    # bloody mess if google decides change their intent structure
    async def get_exec_uid(self, body):
        return body.get("inputs")[0].get("payload").get("commands")[0].get("devices")[0].get("id")
        
    async def get_exec_cmd(self, body):
        return body.get("inputs")[0].get("payload").get("commands")[0].get("execution")[0].get("command")
        
    async def get_exec_param(self, body):
        command = await self.get_exec_cmd(body)
        param = None
        if command == "action.devices.commands.OnOff":
            param = body.get("inputs")[0].get("payload").get("commands")[0].get("execution")[0].get("params").get("on")
            
            deviceOnOff = param # boolean
            param = str(param)
        elif command == "action.devices.commands.SetToggles":
            param = body.get("inputs")[0].get("payload").get("commands")[0].get("execution")[0].get("params").get("updateToggleSettings").get("automatic")
            
            deviceAuto = param # boolean
            
            param = str(param)
        elif command == "action.devices.commands.SetFanSpeed":
            param = body.get("inputs")[0].get("payload").get("commands")[0].get("execution")[0].get("params").get("fanSpeed")
                
            deviceSpeed = param # a string

        return param

    async def create_exec_response(self, requestId, body, param):
        response = myapp.intents.execute_intent
        response["requestId"] = requestId
        
        # these should not error since I've done this already
        UID = await self.get_exec_uid(body)
        command = await self.get_exec_cmd(body)

        response["payload"]["commands"][0]["ids"] = [UID]
        
        if command == "action.devices.commands.OnOff":
            global deviceOnOff
            deviceOnOff = param
            param = True if param == "True" else False
            response["payload"]["commands"][0]["states"] = {"on": param, "online": True}
        elif command == "action.devices.commands.SetToggles":
            param = True if param == "True" else False
            response["payload"]["commands"][0]["states"] = {"currentToggleSettings": {"automatic": param}}
        elif command == "action.devices.commands.SetFanSpeed":
            response["payload"]["commands"][0]["states"] = {"currentFanSpeedSetting": param}
            global deviceSpeed
            deviceSpeed = param
        
        return response
        
    async def send_cmd_backend(self, body, param, backendName):
        
        command = await self.get_exec_cmd(body)
        if command == "action.devices.commands.OnOff":
            if param == "True":
                await self.channel_layer.send(backendName, {"type": "device.on",})
            elif param == "False":
                await self.channel_layer.send(backendName, {"type": "device.off",})
        elif command == "action.devices.commands.SetToggles":
            if param == "True":
                await self.channel_layer.send(backendName, {"type": "device.autoOn",})
            elif param == "False":
                await self.channel_layer.send(backendName, {"type": "device.autoOff",})
        elif command == "action.devices.commands.SetFanSpeed":
            await self.channel_layer.send(backendName, {"type": "device.setSpeed","message":param})
            
        return
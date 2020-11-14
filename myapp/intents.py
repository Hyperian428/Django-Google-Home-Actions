#myapp\intents.py

sync_intent = {
  "requestId": "REPLY THE SAME THING",
  "payload": {
    "agentUserId": "STORED PER USER", # should be unique per user and immutable
    "devices": [
      {
        "id": "JUST USE SERIAL NUMBER", # UID of the device
        "type": "action.devices.types.AIRPURIFIER",
        "traits": [
          "action.devices.traits.OnOff",
          "action.devices.traits.Toggles",
          "action.devices.traits.FanSpeed",
          "action.devices.traits.SensorState"
        ],
        "name": {
          "defaultNames": [
            "Beaugar Purifier" # manu name
          ],
          "name": "Air Purifier",# user can change this from some other command
          "nicknames": [
            "Air Purifier"# other names providied by user
          ]
        },
        "willReportState": True, # needs to be implimented to proactively update google assistant, not sure how this is set, custom data?
        "attributes": {
          "commandOnlyOnOff": False,#report current on off of the device
          "availableFanSpeeds": {
            "speeds": [
             {
              "speed_name": "1",
              "speed_values": [{
                "speed_synonym": ["low", "speed 1"],
                "lang": "en" }]
              },
              {
              "speed_name": "2",
              "speed_values": [{
                "speed_synonym": ["midlow", "speed 2"],
                 "lang": "en" }]
              },
              {
              "speed_name": "3",
              "speed_values": [{
                "speed_synonym": ["mid", "speed 3"],
                 "lang": "en" }]
              },
              {
              "speed_name": "4",
              "speed_values": [{
                "speed_synonym": ["midhigh", "speed 4"],
                 "lang": "en" }]
              },
              {
              "speed_name": "5",
              "speed_values": [{
                "speed_synonym": ["high", "speed 5"],
                 "lang": "en" }]
              }
            ],
            "ordered": True
          },
          "reversible": False,
          "availableToggles": [
            {
              "name": "automatic",
              "name_values": [{
                  "name_synonym": ["automatic", "auto","auto mode", "auto speed"],
                  "lang": "en"}]
            }
          ],
          "sensorStatesSupported": [
            {
              "name": "AirQuality",
              "descriptiveCapabilities": {
                "availableStates": [
                  "healthy",
                  "moderate",
                  "unhealthy"
                ]
              }
            }
          ]
        },
        "deviceInfo": {
          "manufacturer": "Beaugar Works",
          "model": "100",
          "hwVersion": "1.0",
          "swVersion": "1.0"
        }
      }
    ]
  }
}

query_intent = {
  "requestId": "",
  "payload": {
    "devices": {
    }
  }
}

execute_intent = {
  "requestId": "",
  "payload": {
    "commands": [
      {
        "ids": [],
        "status": "SUCCESS",
        "states": {
        }
      }
    ]
  }
}

error_intent = {
  "requestId": "12345",
  "payload": {
    "errorCode": "authFailure",
    "status" : "ERROR"
  }
}

# ESP32 Firmware attached to a dumb Air Purifier

This firmware is based on esp-idf framework, it uses their websocket secure API and WIFI library. The firmware is designed to keep connecting to the backend server, and then send the UID every 10 seconds until it gets its UID in a reply. This is just a simple handshake that IDs the device to the server so the server can send commands to it on-demand.

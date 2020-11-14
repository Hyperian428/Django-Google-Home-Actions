# Django-Google-Home-Actions

This is a Django based Google Home Actions backend that will let you connect to a websocket secure device. You can say "set my device speed to 4" and it will send a specific command through websocket to your device. Currently, the WSS device is a ESP32 board that is hooked up to my dumb air purifier. But It can be any device with Internet capabilities. Google Home Actions use webhooks to communicate with my webhook service.

## Details

This web service uses ASGI and Django Channels to facilitate asynchronous communications between different components of the service. There are 3 main components to this server.
1. A website that allows users to log in and register device ID
2. A webhook service that handles google action's webhook requests
3. A websocket service that handles communication with an ESP32 device. (or any device that supports websocket)

Django models using sqlite3 stores user information and internal state information for each user/device. The asynchronous nature of this server, if extended further, is designed in such a way that it would allow many users and many devices with different device profiles to connect to it.

## Installation
It requires at least Python 3.6.9. Check the [requirements](requirements.txt) to see required packages.
Since this is a Django project, start by installing Django
```bash
pip install Django
```
Clone the project, and go into the root directory.
Use pip to install the required files.
```bash
pip install -r requirements.txt
```

Database needs to be created:
```bash
python manage.py migrate
```
To run the server, you can either use:
```bash
python manage.py runserver
```
But if you are using Heroku, you can also do this:
```bash
heroku local
```
At this point, running the server will probably result in some errors. The server is missing some environmental variables. In a deployed project, leaving secrets and keys in source file is not recommended.
| Vars | Description |
| --- | --- |
| DEBUG_VALUE | True or False |
| PORT | Port you want the server to use |
| REDIS_URL | redis server URL |
| SECRET_KEY | Needed for every Django project |
| SOCIAL_AUTH_AUTH0_DOMAIN | provided by auth0 |
| SOCIAL_AUTH_AUTH0_KEY | provided by auth0 |
| SOCIAL_AUTH_AUTH0_SECRET | provided by auth0 |

### Authentication
I used [Auth0's Django guide](https://auth0.com/docs/quickstart/webapp/django). If you want to use another Authentication service, you'll have to remove the auth0 code in the project.

### Google Action Console
[Action On Google](https://console.actions.google.com) account is required for Home Actions so you can say "set air purifier to speed 5" or "set fan speed to 3". Setting this up with your gmail account will allow your 'device' to show up as a [test]**** brand in the Home Control screen on the app.

The Actions you want to build should be "Home Action". The Fulfillment URL should be the URL that connects to your server, I used ngrok.io to forward requests. It should be something like
```url
https://*****.ngrok.io/webhook/
```

In account linking, if you're using auth0, it would have provided you with client ID and secret. Authorization URL and token URL should also be in the auth0 dashboard.

Additional information might be required for you to deploy a test version of the action, but It should be immediate, meaning you should not need to pay or get account verified since it's a test app that only your email can see.

## Intents
The current intents are referenced from [here](https://developers.google.com/assistant/smarthome/concepts/intents). It can be changed to however you want your device to be seen by Google Assistant.

## End to End Communication
My firmware just serves as a basis as a possible real device connected to the IoT service. [Websocket-device](websocket-device.py) is a simple fake websocket device that replies query command from Google Assistant. The serial in the file should match the UID placed in the website's registration process. Keep websocket_device.py running while using google assistant, and it should reply with query response.

## License
See [LICENSE](LICENSE) file.



# APbackend/routing.py
from django.conf.urls import include, url
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.http import AsgiHandler
from myapp.consumers import backEndConsumer
from myapp.webhook import frontEndConsumer
from myapp import views

application = ProtocolTypeRouter({
    # Empty for now (http->django views is added by default)
    #'websocket': backEndConsumer,
    #'http': frontEndConsumer,

    "websocket": URLRouter([
        url('ws/', backEndConsumer, name='backEndConsumer'),
    ]),
    "http": URLRouter([
        url('webhook/', frontEndConsumer, name='frontEndConsumer'),
        url('', AsgiHandler),  # catch all for handling django views (views needs to be on the sync/wsgi side)
        #url('', views.home, name='home'),
    ]),
})


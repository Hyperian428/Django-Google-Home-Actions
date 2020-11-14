from django.db import models

# Create your models here.
class account(models.Model):
    email = models.EmailField(max_length=254)               # social login
    UID = models.CharField(max_length=10)                   # user enter into form
    frontEndChannelName = models.CharField(max_length=254)  
    backEndChannelName = models.CharField(max_length=254)
    accessToken = models.CharField(max_length=256, default="0")           # from intents
    websocketStatus = models.BooleanField(default = False)
    intentAgentUserId = models.CharField(max_length=256, default = "0")  # from intents
#myapp\views.py
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout as log_out
from django.shortcuts import render, redirect
from django.conf import settings
from django.http import HttpResponseRedirect
from urllib.parse import urlencode
from myapp.models import account
from myapp.forms import UIDForm
import json

def home(request):
    print("Using home view")
    user = request.user
    if user.is_authenticated:
        print("user authenticated")
        return redirect(dashboard)
    else:
        print("user needs authentication")
        return render(request, 'myapp/signin.html')
    #print(request.method)

    #return render(request, 'myapp/base.html')

@login_required
def dashboard(request):
    user = request.user
    userdb = None
    auth0user = user.social_auth.get(provider='auth0')

    userdata = {
        'user_id': auth0user.uid,
        'name': user.first_name,
        'picture': auth0user.extra_data['picture'],
        'email': auth0user.extra_data['email'],
    }

    try:
        userdb = account.objects.get(email=auth0user.extra_data['email'])
    except:
        userdb = account.objects.create(email=auth0user.extra_data['email'])
        print("email doesn't exist, creating database entry")
    
    #print(request.method)
    #print(request.GET)
    # get the UID from user and save it to the email's DB entry
    if request.method == 'POST':
        #print("POST:")
        #print(request.POST)
        form = UIDForm(request.POST)
        if form.is_valid():
            print("valid UID: " + request.POST.get('UID'))
            userdb.UID = request.POST.get('UID')
            userdb.save()
    else:
        form = UIDForm()

    # just doing this for debugging
    allAccounts = account.objects.all()
    context = {
        'accounts': allAccounts,
        'auth0User': auth0user,
        'userdata': json.dumps(userdata, indent=4),
        'UID': form
    }
    
    return render(request, 'myapp/dashboard.html', context)

@login_required
def logout(request):
    log_out(request)
    domain = settings.SOCIAL_AUTH_AUTH0_DOMAIN
    client_id = settings.SOCIAL_AUTH_AUTH0_KEY
    return_to = request.build_absolute_uri('/')
    return HttpResponseRedirect(f'https://{domain}/v2/logout?client_id={client_id}&returnTo={return_to}')


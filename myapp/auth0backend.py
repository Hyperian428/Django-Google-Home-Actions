# myapp/auth0backend.py
from urllib import request
from jose import jwt
from social_core.backends.oauth import BaseOAuth2
class Auth0(BaseOAuth2):
    """Auth0 OAuth authentication backend"""
    name = 'auth0'
    SCOPE_SEPARATOR = ' '
    ACCESS_TOKEN_METHOD = 'POST'
    REDIRECT_STATE = False
    EXTRA_DATA = [
        ('picture', 'picture'),
        ('email', 'email')
    ]

    def authorization_url(self):
        #print("auth0backend: Authorization URL returned")
        # this 'DOMAIN' is from settings.py's SOCIAL_AUTH_AUTH0_DOMAIN
        return 'https://' + self.setting('DOMAIN') + '/authorize'

    def access_token_url(self):
        #print("auth0backend: Access token URL returned")
        return 'https://' + self.setting('DOMAIN') + '/oauth/token'

    def get_user_id(self, details, response):
        """Return current user id."""
        #print("auth0backend: Returned user ID:")
        #print(details)
        return details['user_id']

    def get_user_details(self, response):
        # Obtain JWT and the keys to validate the signature
        id_token = response.get('id_token')
        jwks = request.urlopen('https://' + self.setting('DOMAIN') + '/.well-known/jwks.json')
        issuer = 'https://' + self.setting('DOMAIN') + '/'
        audience = self.setting('KEY')  # CLIENT_ID
        payload = jwt.decode(id_token, jwks.read(), algorithms=['RS256'], audience=audience, issuer=issuer)
        
        return {'username': payload['nickname'],
                'first_name': payload['name'],
                'picture': payload['picture'],
                'user_id': payload['sub'],
                'email': payload['email'],
                'role': payload['https://django-webapp/role'],}
import json
from flask import request, _request_ctx_stack
from functools import wraps
from jose import jwt
from urllib.request import urlopen


AUTH0_DOMAIN = 'dev-nisher.us.auth0.com'
ALGORITHMS = ['RS256']
API_AUDIENCE = 'drinks'

## AuthError Exception
'''
AuthError Exception
A standardized way to communicate auth failure modes
'''
class AuthError(Exception):
    def __init__(self, error, status_code):
        self.error = error
        self.status_code = status_code


## Auth Header

def get_token_auth_header():
    """Validates the Authorization Header and obtains access token from it.

    Returns:
        The token part of the header as a string.
    
    Raises:
        AuthError: An error occurred if no header is present or 
          the header is malformed.
    """

    # Get the header from the request
    auth_header = request.headers.get('Authorization', None)
    
    # Raise an AuthError if no header is present
    if not auth_header:
        raise AuthError({
            'code': 'authorization_header_missing',
            'description': 'Authorization header is missing.'
        }, 401)
    
    # Split bearer and the token
    header_parts = auth_header.split(' ')

    if len(header_parts) != 2:
        raise AuthError({
            'code': 'invalid_header',
            'description': 'Authorization header is malformed.'
        }, 401)
    
    if header_parts[0].lower() != 'bearer':
        raise AuthError({
            'code': 'invalid_header',
            'description': 'Authorization header must start with "Bearer"'
        }, 401)
    
    jwt = header_parts[1]
    return jwt


def check_permissions(permission, payload):
    '''Checks if the requested permission string is in the payload permissions array.

    Args:
        permission: string permission (i.e. 'post:drink').
        payload: decoded jwt payload. 

    Returns:
        A boolean value indicating if the permission string is in the payload permissions array. 
    
    Raises:
        AuthError: An error occurred if permissions array are not included in the payload,
          or the requested permission string is not in the payload permissions array.
    '''
    if 'permissions' not in payload:
        raise AuthError({
            'code': 'invalid_claims',
            'description': 'Permissions are not included in the payload.'
        }, 400)
    

    if permission not in payload['permissions']:
        raise AuthError({
            'code': 'unauthorized',
            'description': 'Permission is not found.'
        }, 403)
    
    return True


def verify_decode_jwt(token):
    '''Verify the input token and decodes the payload from it.
    Arg:
        token: A json web token (string). It should be an Auth0 token with key id (kid)
    
    Returns:
        The decoded payload as a string. 
    
    Raises:
        AuthError: An error occurred if the token is without key id (kid),
          the token is expired, incorrect claims, 
          unable to find the appropriate key, or
          unable to parse authentication token.
    '''

    # Load the public key from Auth0
    url = urlopen(f'https://{AUTH0_DOMAIN}/.well-known/jwks.json')
    jwks = json.loads(url.read())

    # Unpack the jwt header
    unverified_header = jwt.get_unverified_header(token)

    # Check if we have tbe kid to pick which key to validate
    if 'kid' not in unverified_header:
        raise AuthError({
            'code': 'invalid_header',
            'description': 'The jwt header is malformed.'
        }, 401)

    # Choose the appropriate private RSA key
    rsa_key = {}

    for key in jwks['keys']:
        if key['kid'] == unverified_header['kid']:
            rsa_key = {
                'kty': key['kty'],
                'kid': key['kid'],
                'use': key['use'],
                'n': key['n'],
                'e': key['e']
            }
    
    if rsa_key:
        # Use the key to validate and decode the jwt
        try:
            payload = jwt.decode(
                token,
                rsa_key, 
                algorithms=ALGORITHMS, 
                audience=API_AUDIENCE, 
                issuer='https://' + AUTH0_DOMAIN + '/'
            )

            return payload

        except jwt.ExpiredSignatureError:
            raise AuthError({
                'code': 'token_expired',
                'description': 'Token is expired.'
            }, 401)

        except jwt.JWTClaimsError:
            raise AuthError({
                'code': 'invalid_claims',
                'description': 'Incorrect claims. Please check the audience and issuer.'
            }, 401)
        except Exception:
            raise AuthError({
                'code': 'invalid_header',
                'description': 'Unable to decode token.'
            }, 400)

    else:
        raise AuthError({
            'code': 'invalid_header',
            'description': 'Unable to find the appropriate key.'
        }, 400)


def requires_auth(permission=''):
    '''Uses the get_token_auth_header method to get the token,
    Uses the verify_decode_jwt method to decode the jwt,
    Uses the check_permissions method to validate claims and check the requested permission.

    Arg:
        permission: string permission (i.e. 'post:drink').
    
    Returns:
        The decorator which passes the decoded payload to the decorated method.
    '''
    def requires_auth_decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            token = get_token_auth_header()
            payload = verify_decode_jwt(token)
            check_permissions(permission, payload)
            return f(payload, *args, **kwargs)

        return wrapper

    return requires_auth_decorator
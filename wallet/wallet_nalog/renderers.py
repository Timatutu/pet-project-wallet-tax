import json
from rest_framework.renderers import JSONRenderer  

class UserJSONRenderer(JSONRenderer):
    charset = 'utf-8'
    
    def render(self, data, media_type=None, renderer_context=None):
        token = data.get('token', None)
        if token is not None and isinstance(token, bytes):
            data['token'] = token.decode('utf-8')
        
        tokens = data.get('tokens', None)
        if tokens is not None:
            if isinstance(tokens, dict):
                if 'access' in tokens and isinstance(tokens['access'], bytes):
                    tokens['access'] = tokens['access'].decode('utf-8')
                if 'refresh' in tokens and isinstance(tokens['refresh'], bytes):
                    tokens['refresh'] = tokens['refresh'].decode('utf-8')
        
        return super().render(data, media_type, renderer_context)


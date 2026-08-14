import jwt
from urllib.parse import parse_qs
from channels.db import database_sync_to_async
from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.contrib.auth import get_user_model

User = get_user_model()

@database_sync_to_async
def get_user_from_token(token):
    try:
        decoded_data = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        user_id = decoded_data.get('user_id')
        return User.objects.get(id=user_id)
    except Exception:
        return AnonymousUser()

class TokenAuthMiddleware:
    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        query_string = scope.get('query_string', b'').decode('utf-8')
        query_params = parse_qs(query_string)
        token = query_params.get('token')
        
        if token:
            scope['user'] = await get_user_from_token(token[0])
        else:
            scope['user'] = AnonymousUser()
            
        return await self.inner(scope, receive, send)

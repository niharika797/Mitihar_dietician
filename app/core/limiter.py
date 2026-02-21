from slowapi import Limiter
from slowapi.util import get_remote_address

# TODO: Switch to RedisStorage before multi-worker/production deployment
# from slowapi.storage import RedisStorage
# limiter = Limiter(key_func=get_remote_address, storage_uri="redis://localhost:6379")
limiter = Limiter(key_func=get_remote_address)

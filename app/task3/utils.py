import time
from fastapi import Request, HTTPException, Depends
from redis import Redis
from functools import wraps

# Redis client
redis = Redis(host="localhost", port=6379, db=0, decode_responses=True)

def rate_limiter(limit: int = 5, period: int = 1):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, request: Request = None, **kwargs):
            if request:
                user_id = request.headers.get('X-User-ID', request.client.host)
            else:
                # Find the request object in kwargs if not explicitly provided
                request_obj = next((kwargs[k] for k in kwargs if isinstance(kwargs[k], Request)), None)
                user_id = request_obj.headers.get('X-User-ID', request_obj.client.host) if request_obj else 'anonymous'

            # Current timestamp floored to the window
            current_time = int(time.time())
            window_key = f"rate_limit:{user_id}:{current_time}"

            # Increment counter for this window and set expiry
            requests = redis.incr(window_key)
            if requests == 1:
                # Set expiry for new keys (period + 1 to ensure overlap)
                await redis.expire(window_key, period + 1)

            # Check if limit is exceeded
            if requests > limit:
                raise HTTPException(
                    status_code=429,
                    detail="Rate limit exceeded. Try again later."
                )

            # Execute the original function
            return await func(*args, **kwargs)
        return wrapper
    return decorator
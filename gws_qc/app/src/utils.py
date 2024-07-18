def conditional_cache(dec, condition, **kwargs):
    def decorator(func):
        if not condition:
            # Return the function unchanged, not decorated.
            return func
        return dec(func, **kwargs)

    return decorator

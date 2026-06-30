
# annotated  method, using for lock
def locked(lock=None):
    def real_lock(func):
        def wrapper(self, *args, **kwargs):
            lock_obj = getattr(self, lock)
            with lock_obj:
                return func(self, *args, **kwargs)

        return wrapper

    return real_lock


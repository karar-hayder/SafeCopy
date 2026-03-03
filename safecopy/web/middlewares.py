from time import time


class LoggingMiddleware:
    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        start_time = time()
        response = self.app(environ, start_response)
        end_time = time()
        print("Time: ", round((end_time - start_time) * 1000, 2), "ms")
        return response

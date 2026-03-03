import json

from flask import Response


class ResponseDataDTO:
    def __init__(self, items: list = None):
        self.items = items
        self.count = len(items) if items else 0
        self.page = 1
        self.total_pages = (self.count + 9) // 10
        self.has_next = self.page < self.total_pages
        self.has_prev = self.page > 1


class WebResponseDTO:
    def __init__(
        self,
        success: bool,
        data: ResponseDataDTO = None,
        next: str = None,
        prev: str = None,
        error: str = None,
    ):
        self.success = success
        self.data = data
        self.next = next
        self.prev = prev
        self.error = error

    def to_json(self) -> str:
        return json.dumps(self.__dict__)

    def to_response(self) -> Response:
        return Response(self.to_json(), mimetype="application/json")

from enum import Enum
from typing import Optional
from urllib.parse import urljoin

from requests import Session


class PayloadType(str, Enum):
    JSON = 'json'
    MULTIPART = 'multipart'


class APIClient:
    def __init__(self, base_url):
        self.base_url = base_url
        self.session = Session()

    def _build_url(self, path):
        return urljoin(self.base_url, path)

    def _request(self, method, path, requires_auth: bool = True, **kwargs):
        if requires_auth:
            session = self.session
        else:
            session = Session()
        return getattr(session, method)(self._build_url(path), **kwargs)

    def _request_with_payload(self, method, path, data, payload_type: Optional[PayloadType] = None):
        payload_key = {
            PayloadType.JSON: 'json',
            PayloadType.MULTIPART: 'data'
        }.get(payload_type, 'json')
        kwargs = {payload_key: data}
        return self._request(method, path, **kwargs)

    def get(self, path, **kwargs):
        return self._request('get', path, params=kwargs)

    def post(self, path, data, payload_type: Optional[PayloadType] = None):
        return self._request_with_payload('post', path, data, payload_type)

    def put(self, path, data, payload_type: Optional[PayloadType] = None):
        return self._request_with_payload('put', path, data, payload_type)

    def patch(self, path, data, payload_type: Optional[PayloadType] = None):
        return self._request_with_payload('patch', path, data, payload_type)

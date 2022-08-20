from enum import Enum
from typing import Optional, Union, Dict
from urllib.parse import urljoin

from requests import Session, Response

from src.config import ClientConfig


class PayloadType(str, Enum):
    JSON = 'json'
    MULTIPART = 'multipart'


class APIClient:
    def __init__(self, config: ClientConfig) -> None:
        self.base_url = config.base_url
        self.session = Session()
        if config.auth_header is not None:
            self.session.headers = config.auth_header.auth_header

    def _build_url(self, path: str) -> str:
        return urljoin(self.base_url, path)

    def _request(self, method: str, path: str, requires_auth: bool = True, **kwargs) -> Response:
        if requires_auth:
            session = self.session
        else:
            session = Session()
        return getattr(session, method)(self._build_url(path), **kwargs)

    def _request_with_payload(self, method: str, path: str, data: Union[Dict, str],
                              payload_type: Optional[PayloadType] = None) -> Response:
        payload_key = {
            PayloadType.JSON: 'json',
            PayloadType.MULTIPART: 'data'
        }.get(payload_type, 'json')
        kwargs = {payload_key: data}
        return self._request(method, path, **kwargs)

    def get(self, path: str, **kwargs) -> Response:
        return self._request('get', path, params=kwargs)

    def post(self, path: str, data: Union[Dict, str], payload_type: Optional[PayloadType] = None) -> Response:
        return self._request_with_payload('post', path, data, payload_type)

    def put(self, path: str, data: Union[Dict, str], payload_type: Optional[PayloadType] = None) -> Response:
        return self._request_with_payload('put', path, data, payload_type)

    def patch(self, path: str, data: Union[Dict, str], payload_type: Optional[PayloadType] = None) -> Response:
        return self._request_with_payload('patch', path, data, payload_type)

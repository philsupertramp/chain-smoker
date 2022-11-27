import base64
import gzip
import os
import re
import urllib.parse
from typing import Optional, Dict, List

import yaml
from pydantic import BaseModel, Field

from src.chain_smoker.config import TestCaseConfig, ConfigType, Response, Request
from src.chain_smoker.mixins import EvaluationMixin


def is_base64(s):
    try:
        return base64.b64encode(base64.b64decode(s)) == s.encode()
    except Exception:
        return False


class RewriteConfig(BaseModel):
    skip: Dict
    skip_files: List
    headers: Dict
    requests: Dict

    @classmethod
    def from_file(cls, filename):
        if filename is None:
            filename = os.path.join(os.path.dirname(__file__), '../../conf/parse-conf.yaml')

        content = {'skip': {}, 'skip_files': [], 'headers': {}, 'requests': {}}

        try:
            with open(filename, 'r') as file:
                file_content = next(yaml.full_load_all(file))
            content.update(file_content)
        except FileNotFoundError:
            pass

        return cls(**content)

    def apply(self, request, obj, conf_key, replace=False, regex_replace=False):
        url = urllib.parse.urlparse(request.Path)
        if url.path in self.requests:
            conf = self.requests[url.path]
            if request.Method.lower() in conf:
                conf = conf[request.Method.lower()]
                if conf.get(conf_key):
                    if replace:
                        for key, value in conf.get(conf_key, {}).items():
                            if key in obj:
                                obj[key] = value
                    elif regex_replace:
                        output = []
                        for value in conf.get(conf_key):
                            match = re.findall(fr'{value}', obj)
                            if match:
                                output.extend(match)
                        obj = output
                    else:
                        for key in conf.get(conf_key, []):
                            if key in obj:
                                del obj[key]
        return obj


class TestFileWriter(BaseModel, EvaluationMixin):
    request: Request = Field()
    response: Response = Field()
    target_file: str = Field()
    config: Optional[RewriteConfig] = Field()

    def __init__(self, request_dict, target_file: str, config_file: Optional[str] = None):
        super().__init__(
            request=Request(**request_dict.get('Request', {})),
            response=Response(**request_dict.get('Response', {})),
            target_file=target_file,
            config=RewriteConfig.from_file(config_file)
        )

    def _clean_response(self, response):
        return self.config.apply(
            self.request,
            self.config.apply(self.request, response, 'ignore_response'),
            'keep',
            regex_replace=True
        )

    def _clean_payload(self, payload):
        return self.config.apply(self.request, payload, 'payload', replace=True)

    def _build_payload(self):
        payload = ''
        if self.request.Payload:
            payload = self._clean_payload(self.evaluate_value(self.request.Payload))
        return payload

    def _build_body(self):
        if is_base64(self.response.Body):
            body = base64.b64decode(self.response.Body)
        else:
            body = self.response.Body
        if 'zip' in self.request.Headers.get('Accept-Encoding', [''])[0]:
            body = str(gzip.decompress(body), 'utf-8')
        elif isinstance(body, str) and '<html' in body.lower():
            body = self._clean_response(body)
        else:
            body = self._clean_response(self.evaluate_value(body))
        return body

    def _build_config(self):
        url = urllib.parse.urlparse(self.request.Path)
        test_name = f'{self.request.Method.lower()}-{str(url.hostname).replace(".", "_")}{url.path.replace("/", "__")}'
        payload = self._build_payload()
        body = self._build_body()
        config = TestCaseConfig.from_dict(dict(
            type=ConfigType.API_TEST,
            config=dict(
                client=dict(
                    base_url=f'{url.scheme}://{url.hostname}'
                )
            ),
            tests={
                test_name: dict(
                    name=test_name,
                    method=self.request.Method.lower(),
                    endpoint=f'{url.path}{f"?{url.query}" if url.query else ""}',
                    payload=payload,
                    expects_status_code=self.response.Status_code,
                    contains=body,
                    headers={
                        key: f'[{",".join(value)}]' if isinstance(value, list) else str(value)
                        for key, value in {**self.config.headers, **self.request.Headers}.items()
                    }
                )
            }
        ))
        obj_dict = config.dict()
        obj_dict['type'] = obj_dict['type'].value
        return obj_dict

    def write(self):
        url = urllib.parse.urlparse(self.request.Path)
        if url.path in self.config.skip and self.request.Method.upper() in self.config.skip[url.path]:
            return
        for path in self.config.skip_files:
            if path in url.path:
                return
        config = self._build_config()

        with open(self.target_file, 'w') as file:
            yaml.dump(config, file)

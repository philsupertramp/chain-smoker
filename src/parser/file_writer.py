import os
import urllib.parse
from typing import Optional, Dict

import yaml
from pydantic import BaseModel, Field

from src.chain_smoker.config import TestCaseConfig, ConfigType, Response, Request
from src.chain_smoker.mixins import EvaluationMixin


class RewriteConfig(BaseModel):
    skip: Dict
    headers: Dict
    requests: Dict

    @classmethod
    def from_file(cls, filename):
        if filename is None:
            filename = os.path.join(os.path.dirname(__file__), '../../conf/parse-conf.yaml')

        content = {'skip': {}, 'headers': {}, 'requests': {}}

        try:
            with open(filename, 'r') as file:
                file_content = next(yaml.full_load_all(file))
            content.update(file_content)
        except FileNotFoundError:
            pass

        return cls(**content)


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

    def _clean_dict(self, obj, conf_key, replace=False):
        url = urllib.parse.urlparse(self.request.Path)
        if url.path in self.config.requests:
            conf = self.config.requests[url.path]
            if self.request.Method.lower() in conf:
                conf = conf[self.request.Method.lower()]
                if conf.get(conf_key):
                    if replace:
                        for key, value in conf.get(conf_key, {}).items():
                            if key in obj:
                                obj[key] = value
                    else:
                        for key in conf.get(conf_key, []):
                            if key in obj:
                                del obj[key]
        return obj

    def _clean_response(self, response):
        return self._clean_dict(response, 'ignore_response')

    def _clean_payload(self, payload):
        return self._clean_dict(payload, 'payload', replace=True)

    def _build_config(self):
        url = urllib.parse.urlparse(self.request.Path)
        test_name = f'{self.request.Method.lower()}-{str(url.hostname).replace(".", "_")}{url.path.replace("/", "__")}'
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
                    payload=self._clean_payload(self.evaluate_value(self.request.Payload or '{}')),
                    expects_status_code=self.response.Status_code,
                    contains=self._clean_response(self.evaluate_value(self.response.Body)),
                    headers=self.config.headers
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
        config = self._build_config()

        with open(self.target_file, 'w') as file:
            yaml.dump(config, file)

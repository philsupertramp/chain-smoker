import urllib.parse

import yaml
from pydantic import BaseModel, Field

from src.chain_smoker.config import TestCaseConfig, ConfigType, Response, Request
from src.chain_smoker.mixins import EvaluationMixin


class TestFileWriter(BaseModel, EvaluationMixin):
    request: Request = Field()
    response: Response = Field()
    target_file: str = Field()

    def __init__(self, request_dict, target_file: str):
        super().__init__(
            request=Request(**request_dict.get('Request', {})),
            response=Response(**request_dict.get('Response', {})),
            target_file=target_file
        )

    def _build_config(self):
        url = urllib.parse.urlparse(self.request.Path)
        test_name = f'{self.request.Method.lower()}-{str(url.hostname).replace(".", "_")}{url.path.replace("/", "__")}'
        config = TestCaseConfig.from_dict(dict(
            type=ConfigType.API_TEST,
            config=dict(
                client=dict(
                    base_url=f'{url.scheme}://{url.hostname}'
                ),
                env={}
            ),
            tests={
                test_name: dict(
                    name=test_name,
                    method=self.request.Method.lower(),
                    endpoint=f'{url.path}{f"?{url.query}" if url.query else ""}',
                    payload=self.evaluate_value(self.request.Payload or '{}'),
                    expects_status_code=self.response.Status_code,
                    expected=self.evaluate_value(self.response.Body)
                )
            }
        ))
        obj_dict = config.dict()
        obj_dict['type'] = obj_dict['type'].value
        return obj_dict

    def write(self):
        config = self._build_config()

        with open(self.target_file, 'w') as file:
            yaml.dump(config, file)

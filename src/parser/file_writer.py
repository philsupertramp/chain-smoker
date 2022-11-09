import urllib.parse

import yaml

from src.chain_smoker.config import TestCaseConfig, ConfigType, TestFileConfig, ClientConfig, TestConfig
from src.chain_smoker.mixins import EvaluationMixin


class TestFileWriter(EvaluationMixin):
    def __init__(self, request_dict, target_file: str):
        self.request = request_dict.get('Request')
        self.response = request_dict.get('Response')
        self.target_file = target_file

    def _build_config(self):
        url = urllib.parse.urlparse(self.request.get('Path'))
        config = TestCaseConfig(
            type=ConfigType.API_TEST,
            config=TestFileConfig(
                client=ClientConfig(
                    base_url=f'{url.scheme}://{url.hostname}'
                ),
            ),
            tests=[
                TestConfig(
                    name=f'{self.request.get("Method").lower()}_{url.hostname}_{url.path.replace("/", "_")}',
                    method=self.request.get('Method').lower(),
                    endpoint=f'{url.path}?{url.query}',
                    payload=self.evaluate_value(self.request.get('Payload', "{}") or "{}"),
                    expected_status_code=self.response.get('Status_code'),
                    expected=self.evaluate_value(self.response.get('Body', "{}"))
                )
            ]
        )
        obj_dict = config.dict()
        obj_dict['type'] = ConfigType.API_TEST.value
        obj_dict['tests'] = {obj.get('name'): obj for obj in obj_dict['tests']}
        return obj_dict

    def write(self):
        config = self._build_config()

        with open(self.target_file, 'w') as file:
            yaml.dump(config, file)

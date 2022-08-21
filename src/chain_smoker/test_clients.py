from typing import Union, Dict, Callable, List
from functools import partial

from .api_client import APIClient
from .config import TestConfig
from .logger import logger
from .mixins import ExpectedMixin


class SmokeTest:
    def __init__(self, name: str, method: Callable, expected_result: Union[Dict, str, int],
                 contains_result: Union[Dict, str, int]) -> None:
        self.name: str = name
        self.method: Callable = method
        self.expected_result: Union[Dict, str, int] = expected_result
        self.contains_result: Union[Dict, str, int] = contains_result

    def _get_response(self, *args, **kwargs):
        res = self.method(*args, **kwargs)
        try:
            return res.json()
        except ValueError:
            return res.text.replace('\n', '').replace('   ', ' ').replace('  ', ' ')

    def run(self, *args, **kwargs) -> None:
        result = self._get_response(*args, **kwargs)
        if self.expected_result is not None and result != self.expected_result:
            logger.error(f'Unexpected result for {self.name}!\n{result}\n!=\n{self.expected_result}\n{self.method}')
            return
        if self.contains_result is not None:
            if isinstance(self.contains_result, str):
                if self.contains_result not in result:
                    logger.error(f'Unexpected result for {self.name}!\n{self.contains_result} not found in:\n{result}')
                    return
            else:
                for key, value in self.contains_result.items():
                    if key not in result:
                        logger.error(f'Unexpected result for {self.name}!\n{key} not found in:\n{result}')
                        return
                    if result[key] != value:
                        logger.error(f'Unexpected result for {self.name}!\n{result[key]}!={value}\n{self.method}')
                        return
        logger.info(f'Success for {self.name}!')


class ChainedSmokeTest(ExpectedMixin):
    def __init__(self, name: str, steps: List[TestConfig], client: APIClient):
        self.name: str = name
        self.steps: List[TestConfig] = steps
        self.client: APIClient = client
        self.tests: List[SmokeTest] = list()
        self._build_test()

    def _build_test(self):
        for step in self.steps:
            if step.is_authentication:
                res = getattr(self.client, step.method)(step.endpoint, data=self.build_expected(step.payload))
                auth_key, auth_value = list(step.auth_header_template.auth_header.dict().items())[0]
                auth_value = auth_value.format(token=eval(step.auth_header_template.token_position))
                self.client.session.headers = {auth_key: auth_value}
            else:
                self.tests.append(SmokeTest(
                    step.name,
                    partial(getattr(self.client, step.method), step.endpoint),
                    self.build_expected(step.expected),
                    step.contains,
                ))

    def run(self):
        for test in self.tests:
            test.run()

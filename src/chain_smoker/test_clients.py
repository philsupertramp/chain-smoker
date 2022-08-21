from typing import Union, Dict, Callable, List
from functools import partial

from .api_client import APIClient
from .config import TestConfig
from .logger import logger
from .mixins import ExpectedMixin


class ValueTest:
    def __init__(self, value: Union[Dict, str, int]):
        self.value = value

    def _run_test(self, other_value: Union[Dict, str, int], name: str, method: Callable) -> None:
        raise NotImplementedError()

    def test(self, other_value: Union[Dict, str, int], name: str, method: Callable) -> bool:
        self.error = ''
        self.found_error = False
        self._run_test(other_value, name, method)
        if self.found_error:
            logger.error(self.error)
        return not self.found_error


class ExpectedTest(ValueTest):
    def _run_test(self, other_value: Union[Dict, str, int], name: str, method: Callable) -> None:
        if other_value != self.value:
            self.error = f'Unexpected result for {name}!\n{other_value}\n!=\n{self.value}\n{method}'
            self.found_error = True


class ContainsTest(ValueTest):
    def _run_test(self, other_value: Union[Dict, str, int], name: str, method: Callable) -> None:
        if isinstance(self.value, str):
            if self.value not in other_value:
                self.error = f'Unexpected result for {name}!\n' \
                             f'{self.value} not found in:\n' \
                             f'{other_value}'
                self.found_error = True
        else:
            for key, value in self.value.items():
                if isinstance(value, dict):
                    for nested_key, nested_value in value.items():
                        if nested_key not in other_value[key]:
                            self.error = f'Unexpected result for {name}!\n' \
                                         f'{nested_key} not found in:\n' \
                                         f'{other_value[key]}'
                            self.found_error = True
                        if other_value[key][nested_key] != nested_value:
                            self.error = f'Unexpected result for {name}!\n' \
                                         f'{other_value[key][nested_key]}!={nested_value}\n' \
                                         f'{method}'
                            self.found_error = True
                else:
                    if key not in other_value:
                        self.error = f'Unexpected result for {name}!\n{key} not found in:\n{other_value}'
                        self.found_error = True
                    if other_value[key] != value:
                        self.error = f'Unexpected result for {name}!\n{other_value[key]}!={value}\n{method}'
                        self.found_error = True


class SmokeTest(ExpectedMixin):
    def __init__(self, name: str, method: Callable, expected_result: Union[Dict, str, int],
                 contains_result: Union[Dict, str, int]) -> None:
        self.name: str = name
        self.method: Callable = method
        self.expected_result: ExpectedTest = ExpectedTest(expected_result) if expected_result else None
        self.contains_result: ContainsTest = ContainsTest(contains_result) if contains_result else None

    def _get_response(self, *args, **kwargs):
        res = self.method(*args, **kwargs)
        try:
            return res.json()
        except ValueError:
            return res.text.replace('\n', '').replace('   ', ' ').replace('  ', ' ')

    def run(self, *args, **kwargs) -> None:
        result = self._get_response(*args, **kwargs)
        if self.expected_result is not None and not self.expected_result.test(result, self.name, self.method):
            return
        if self.contains_result is not None and not self.contains_result.test(result, self.name, self.method):
            return
        logger.info(f'Success for {self.name}!')

    @classmethod
    def build(cls, step: TestConfig, client: APIClient) -> 'SmokeTest':
        if step.payload is not None:
            method = partial(getattr(client, step.method), step.endpoint, step.payload)
        else:
            method = partial(getattr(client, step.method), step.endpoint)
        return cls(
            step.name,
            method,
            cls.build_expected(step.expected),
            step.contains
        )


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
                self.tests.append(SmokeTest.build(
                    step,
                    self.client
                ))

    def run(self):
        for test in self.tests:
            test.run()

    @classmethod
    def build(cls, step: TestConfig, client: APIClient) -> 'ChainedSmokeTest':
        return cls(step.name, step.steps, client)

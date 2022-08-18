import ast
import json
import logging
import os
import sys
from typing import List

import yaml
from functools import partial

from src.api_client import APIClient


file_handler = logging.FileHandler(filename='tmp.log')
stdout_handler = logging.StreamHandler(stream=sys.stdout)
handlers = [file_handler, stdout_handler]

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s - %(message)s',
    handlers=handlers
)
logger = logging.getLogger('SMOKE_TESTER')


class SmokeTest:
    def __init__(self, name, method, expected_result, contains_result):
        self.name = name
        self.method = method
        self.expected_result = expected_result
        self.contains_result = contains_result

    def run(self, *args, **kwargs):
        result = self.method(*args, **kwargs).json()
        if self.expected_result is not None and result != self.expected_result:
            logger.error(f'Unexpected result for {self.name}!\n{result}\n!=\n{self.expected_result}\n{self.method}')
            return
        if self.contains_result is not None:
            for key, value in self.contains_result.items():
                if key not in result:
                    logger.error(f'Unexpected result for {self.name}!\n{key} not found in:\n{result}')
                    return
                if result[key] != value:
                    logger.error(f'Unexpected result for {self.name}!\n{result[key]}!={value}\n{self.method}')
                    return
        logger.info(f'Success for {self.name}!')


class ChainedSmokeTest:
    def __init__(self, name, steps, client):
        self.name = name
        self.steps = steps
        self.client = client
        self.tests = list()
        self._build_test()

    def _build_test(self):
        for step in self.steps:
            if step.get('is_authentication'):
                res = getattr(self.client, step.get('method', 'post'))(step.get('endpoint'), data=ast.literal_eval(step.get('payload')))
                auth_key, auth_value = list(step.get('auth_header_template').get('auth_header').items())[0]
                auth_value = auth_value.format(token=eval(step.get('auth_header_template').get('token_position')))
                self.client.session.headers = {auth_key: auth_value}
            else:
                expected_value = step.get('expected')
                expected = None
                if expected_value:
                    try:
                        expected = ast.literal_eval(expected_value)
                    except ValueError:
                        expected = json.loads(expected_value)
                contains = step.get('contains')
                test_case = SmokeTest(
                    step.get('name'),
                    partial(
                        getattr(self.client, step.get('method', 'get')),
                        step.get('endpoint')
                    ),
                    expected,
                    contains,
                )
                self.tests.append(test_case)

    def run(self):
        for test in self.tests:
            test.run()


class TestFileLoader:
    def __init__(self, filename):
        self.filename = filename
        self.content = self._load_content(filename)
        self.client = None
        self.test_methods: List[SmokeTest] = list()
        self._bootstrap()

    @staticmethod
    def _load_content(filename):
        with open(filename, 'r') as stream:
            data_loaded = yaml.safe_load(stream)
        return data_loaded

    @staticmethod
    def _get_client(content):
        if content.get('type') == 'api-test':
            return APIClient(content.get('config', {}).get('client', {}).get('base_url'))

    def _build_tests(self):
        for test_name, test_config in self.content.get('tests', {}).items():
            if test_config.get('multi_step'):
                test_case = ChainedSmokeTest(
                    test_name,
                    test_config.get('steps', []),
                    self.client
                )
            else:
                expected = test_config.get('expected')
                contains = test_config.get('contains')
                test_case = SmokeTest(
                    test_name,
                    partial(
                        getattr(self.client, test_config.get('method', 'get')),
                        test_config.get('endpoint')
                    ),
                    ast.literal_eval(expected),
                    contains,
                )
            self.test_methods.append(test_case)

    def _bootstrap(self):
        self.client = self._get_client(self.content)
        self._build_tests()

    def run(self):
        logger.info(f'Running for {self.filename}:')
        for test in self.test_methods:
            test.run()


if __name__ == '__main__':
    files = filter(lambda f: '.yaml' in f, os.listdir('smoke_tests'))
    for file in files:
        loader = TestFileLoader(os.path.join("smoke_tests/", file))

        loader.run()

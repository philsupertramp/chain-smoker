from functools import partial
from typing import List, Optional

import yaml

from src.api_client import APIClient
from src.config import TestCaseConfig
from src.logger import logger
from src.mixins import ExpectedMixin
from src.test_clients import SmokeTest, ChainedSmokeTest


class TestFileLoader(ExpectedMixin):
    def __init__(self, filename: str):
        self.filename = filename
        content = self._load_content(filename)
        self.config: TestCaseConfig = TestCaseConfig.from_dict(content)
        self.client: Optional[APIClient] = None
        self.test_methods: List[SmokeTest] = list()
        self._bootstrap()

    @staticmethod
    def _load_content(filename):
        with open(filename, 'r') as stream:
            data_loaded = yaml.safe_load(stream)
        return data_loaded

    @staticmethod
    def _get_client(config: TestCaseConfig) -> Optional[APIClient]:
        if config.type == 'api-test':
            return APIClient(config.config.client)

    def _build_tests(self) -> None:
        for test_config in self.config.tests:
            if test_config.multi_step:
                test_case = ChainedSmokeTest(
                    test_config.name,
                    test_config.steps,
                    self.client
                )
            else:
                test_case = SmokeTest(
                    test_config.name,
                    partial(getattr(self.client, test_config.method), test_config.endpoint),
                    self.build_expected(test_config.expected),
                    test_config.contains,
                )
            self.test_methods.append(test_case)

    def _bootstrap(self) -> None:
        self.client = self._get_client(self.config)
        self._build_tests()

    def run(self) -> None:
        logger.info(f'Running for {self.filename}:')
        for test in self.test_methods:
            test.run()

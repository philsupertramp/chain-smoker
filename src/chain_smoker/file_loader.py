from functools import partial
from typing import List, Optional

import yaml

from .api_client import APIClient
from .config import TestCaseConfig, ConfigType
from .logger import logger
from .mixins import ExpectedMixin
from .test_clients import SmokeTest, ChainedSmokeTest


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
            data_loaded = yaml.full_load_all(stream)
        return data_loaded

    @staticmethod
    def _get_client(config: TestCaseConfig) -> Optional[APIClient]:
        if config.type == ConfigType.API_TEST:
            return APIClient(config.config.client)

    def _build_tests(self) -> None:
        for test_config in self.config.tests:
            if test_config.multi_step:
                test_case = ChainedSmokeTest.build(test_config, self.client)
            else:
                test_case = SmokeTest.build(test_config, self.client)
            self.test_methods.append(test_case)

    def _bootstrap(self) -> None:
        self.client = self._get_client(self.config)
        self._build_tests()

    def run(self) -> None:
        logger.info(f'Running for {self.filename}:')
        for test in self.test_methods:
            test.run()

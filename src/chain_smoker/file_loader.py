import os
from typing import List, Optional, Dict, Any

import yaml

from .api_client import APIClient
from .config import TestCaseConfig, ConfigType, EnvVar
from .logger import logger
from .mixins import EvaluationMixin
from .test_clients import SmokeTest, ChainedSmokeTest


class TestFileLoader(EvaluationMixin):
    def __init__(self, filename: str):
        self.filename = filename
        content = self._load_content(filename)
        self.config: TestCaseConfig = TestCaseConfig.from_dict(content)
        self.client: Optional[APIClient] = self._get_client(self.config)
        self.env_vars: Dict[str, Any] = self._get_env_vars(self.config)
        self.test_methods: List[SmokeTest] = list()
        self._build_tests()

    @staticmethod
    def _load_content(filename):
        with open(filename, 'r') as stream:
            data_loaded = next(yaml.full_load_all(stream))
        return data_loaded

    @staticmethod
    def _get_client(config: TestCaseConfig) -> Optional[APIClient]:
        if config.type == ConfigType.API_TEST:
            return APIClient(config.config.client)

    @staticmethod
    def _get_env_vars(config: TestCaseConfig) -> Dict[str, Any]:
        out = {}
        for env_var in config.config.env:
            out[env_var.internal_key] = os.environ.get(env_var.external_key)
        return out

    def _build_tests(self) -> None:
        self.test_methods = list()
        for test_config in self.config.tests:
            if test_config.multi_step:
                test_case = ChainedSmokeTest.build(test_config, self.client)
            else:
                test_case = SmokeTest.build(test_config, self.client)
            self.test_methods.append(test_case)

    def run(self) -> None:
        logger.info(f'Running for {self.filename}:')
        for test in self.test_methods:
            test.run(env=self.env_vars)

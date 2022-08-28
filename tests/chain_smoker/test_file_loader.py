import os
from unittest import TestCase, mock

from src.chain_smoker.api_client import APIClient
from src.chain_smoker.file_loader import TestFileLoader


class FileLoaderTestCase(TestCase):
    sample_file_name = os.path.join(os.path.dirname(__file__), 'fixtures/sample.yaml')

    def test_load_content(self):
        expected_output = {
            'type': 'api-test',
            'config': {'client': {'base_url': 'https://example.com'}},
            'tests': {
                'test_something': {
                    'method': 'get',
                    'status_code': 200,
                    'contains': 'This domain is for use in illustrative examples in documents. You may use this '
                                'domain in literature without prior coordination or asking for permission.'
                },
                'test_same_request_twice': {
                    'multi_step': True,
                    'steps': [
                        {'name': 'first_request', 'method': 'get', 'status_code': 200},
                        {'name': 'second_request', 'method': 'get', 'status_code': 200},
                    ]
                }
            }
        }
        out = TestFileLoader._load_content(self.sample_file_name)

        self.assertDictEqual(out, expected_output)

    def test_get_client(self):
        loader = TestFileLoader(self.sample_file_name)
        client = TestFileLoader._get_client(loader.config)

        self.assertTrue(isinstance(client, APIClient))

        config = loader.config
        config.type = None

        self.assertIsNone(TestFileLoader._get_client(config))

    def test_build_tests(self):
        loader = TestFileLoader(self.sample_file_name)

        self.assertEqual(len(loader.test_methods), 2)
        self.assertEqual(loader.test_methods[0].name, 'test_something')

        loader._build_tests()

        self.assertEqual(len(loader.test_methods), 2)
        self.assertEqual(loader.test_methods[0].name, 'test_something')

    def test_bootstrap(self):
        loader = TestFileLoader(self.sample_file_name)

        loader.client = None
        loader.test_methods = list()

        loader._bootstrap()

        self.assertIsNotNone(loader.client)
        self.assertEqual(len(loader.test_methods), 2)
        self.assertEqual(loader.test_methods[0].name, 'test_something')

    def test_run(self):
        loader = TestFileLoader(self.sample_file_name)
        test_mock = mock.Mock()
        loader.test_methods = [test_mock]

        loader.run()

        test_mock.run.assert_called_once()
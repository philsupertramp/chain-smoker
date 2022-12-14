import os
from unittest import TestCase, mock

from src.chain_smoker.api_client import APIClient
from src.chain_smoker.file_loader import TestFileLoader


class FileLoaderTestCase(TestCase):
    sample_file_name = os.path.join(os.path.dirname(__file__), 'fixtures/sample.yaml')

    def test_empty_constructor(self):
        with self.assertRaises(AssertionError) as err:
            TestFileLoader()

        self.assertIn('Requires `cfg` in case no `filename` provided.', str(err.exception))

    @mock.patch.dict(os.environ, {'bar': 'baz'})
    def test_load_content(self):
        expected_output = {
            'type': 'api-test',
            'config': {'client': {'base_url': 'https://example.com'}, 'env': {'foo': 'bar'}},
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
                },
                'test_using_env': {
                    'method': 'get',
                    'status_code': 200,
                    'endpoint': '{env.get("foo")}'
                }
            }
        }
        out = TestFileLoader._load_content(self.sample_file_name)

        self.assertDictEqual(out, expected_output)

    @mock.patch.dict(os.environ, {'bar': 'baz'})
    def test_get_client(self):
        loader = TestFileLoader(self.sample_file_name)
        client = TestFileLoader._get_client(loader.config)

        self.assertTrue(isinstance(client, APIClient))

        config = loader.config
        config.type = None

        self.assertIsNone(TestFileLoader._get_client(config))

    @mock.patch.dict(os.environ, {'bar': 'baz'})
    def test_build_tests(self):
        loader = TestFileLoader(self.sample_file_name)

        self.assertEqual(len(loader.test_methods), 3)
        self.assertEqual(loader.test_methods[0].name, 'test_something')

        loader._build_tests()

        self.assertEqual(len(loader.test_methods), 3)
        self.assertEqual(loader.test_methods[0].name, 'test_something')

    @mock.patch.dict(os.environ, {'bar': 'baz'})
    def test_run(self):
        loader = TestFileLoader(self.sample_file_name)
        test_mock = mock.Mock()
        loader.test_methods = [test_mock]

        loader.run()

        test_mock.run.assert_called_once()

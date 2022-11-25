import os
import tempfile
from unittest import TestCase, mock

import yaml
from parameterized import parameterized
from pydantic import ValidationError

from src.chain_smoker.file_loader import TestFileLoader
from src.parser.file_writer import TestFileWriter, RewriteConfig


class FileWriterTestCase(TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.sample_request = {
            'Request': {
                'Method': 'get', 'Path': 'https://example.com/get/', 'Payload': {},
                'Protocol': 'HTTP/1', 'Headers': {},
            },
            'Response': {
                'Status_code': 200, 'Body': {'foo': 1, 'bar': 'xxxxxx'}, 'Headers': {},
            }
        }
        cls.html_sample_request = {
            'Request': {
                'Method': 'get', 'Path': 'https://example.com/get/', 'Payload': {},
                'Protocol': 'HTTP/1', 'Headers': {},
            },
            'Response': {
                'Status_code': 200, 'Body': '<html><h1>Hello World!</h1></html>', 'Headers': {},
            }
        }
        cls.zipped_html_sample_request = {
            'Request': {
                'Method': 'get', 'Path': 'https://example.com/get/', 'Payload': {},
                'Protocol': 'HTTP/1', 'Headers': {'Accept-Encoding': ['gzip', 'deflate', 'br']},
            },
            'Response': {
                'Status_code': 200, 'Body': '\x1F\uFFFD\b\0\0\0\0\0', 'Headers': {},
            }
        }
        cls.post_sample_request = {
            'Request': {
                'Method': 'post', 'Path': 'https://example.com/post/', 'Payload': {'foo': 1, 'bar': 'xxxxxx'},
                'Protocol': 'HTTP/1', 'Headers': {},
            },
            'Response': {
                'Status_code': 200, 'Body': {'foo': 1, 'bar': 'xxxxxx'}, 'Headers': {},
            }
        }

    def test_constructor(self):
        with self.assertRaises(ValidationError):
            TestFileWriter({}, 'foo.yml')
        with self.assertRaises(ValidationError):
            TestFileWriter({
                'Request': {},
                'Response': {'Status_code': 200, 'Body': {}, 'Headers': {}}
            }, 'foo.yml')

        with self.assertRaises(ValidationError):
            TestFileWriter({
                'Request': {'Method': 'get', 'Path': '/', 'Payload': {}, 'Protocol': 'HTTP/1', 'Headers': {}},
                'Response': {}
            }, 'foo.yml')

        with self.assertRaises(ValidationError):
            TestFileWriter({
                'Request': {'missing-key': 'get', 'Path': '/', 'Payload': {}, 'Protocol': 'HTTP/1', 'Headers': {}},
                'Response': {'Status_code': 200, 'Body': {}, 'Headers': {}}
            }, 'foo.yml')

        with self.assertRaises(ValidationError):
            TestFileWriter({
                'Request': {'Method': 'get', 'Path': '/', 'Payload': {}, 'Protocol': 'HTTP/1', 'Headers': {}},
                'Response': {'Status_code': 200, 'missing-key': {}, 'Headers': {}}
            }, 'foo.yml')

        # ok
        TestFileWriter({
            'Request': {'Method': 'get', 'Path': '/', 'Payload': {}, 'Protocol': 'HTTP/1', 'Headers': {}},
            'Response': {'Status_code': 200, 'Body': {}, 'Headers': {}}
        }, 'foo.yml')

    def test_build_config(self):
        writer = TestFileWriter(self.sample_request, 'foo.yml')

        config = writer._build_config()
        test = TestFileLoader(cfg=config)

        self.assertEqual(len(test.test_methods), 1)
        method = test.test_methods[0]

        self.assertEqual(method.endpoint, '/get/')
        self.assertEqual(method.method, 'get')
        self.assertEqual(method.payload, '')
        self.assertEqual(method.expects_status_code.value, 200)
        self.assertEqual(method.client.base_url, 'https://example.com')

    def test_write(self):
        with tempfile.TemporaryDirectory() as tempdir:
            # you can e.g. create a file here:
            tmpfilepath = os.path.join(tempdir, 'someFileInTmpDir.yaml')

            with self.assertRaises(ValidationError):
                TestFileWriter({}, tmpfilepath)

            with self.assertRaises(ValidationError):
                TestFileWriter(self.sample_request, None)

            writer = TestFileWriter(self.sample_request, tmpfilepath)
            writer.config.skip = {'/get/': ['GET']}

            writer.write()
            self.assertFalse(os.path.exists(tmpfilepath))

            writer.config.skip = {}
            writer.write()
            self.assertTrue(os.path.exists(tmpfilepath))
            os.remove(tmpfilepath)

            # fixed path
            writer.config.skip_files = ['/styles.css']
            writer.request.Path = '/styles.css'
            writer.write()
            self.assertFalse(os.path.exists(tmpfilepath))

            # file ending wild card
            writer.config.skip_files = ['.css']
            writer.request.Path = '/styles.css'
            writer.write()
            self.assertFalse(os.path.exists(tmpfilepath))

            # sub-page wild card
            writer.config.skip_files = ['/hidden/']
            writer.request.Path = '/hidden/styles.css'
            writer.write()
            self.assertFalse(os.path.exists(tmpfilepath))

            # wild card mismatch
            writer.config.skip_files = ['/hidden/']
            writer.request.Path = '/styles.css'
            writer.write()
            self.assertTrue(os.path.exists(tmpfilepath))
            os.remove(tmpfilepath)

    @mock.patch('src.chain_smoker.api_client.APIClient.get')
    def test_can_use_built_config(self, get_mock):
        get_mock.return_value = mock.Mock(
            json=mock.Mock(return_value={'foo': 1, 'bar': 'xxxxxx'}),
            status_code=200
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            # you can e.g. create a file here:
            temp_file_path = os.path.join(temp_dir, 'someFile.yaml')
            writer = TestFileWriter(self.sample_request, temp_file_path)
            writer.write()

            test = TestFileLoader(temp_file_path)
            test_method = test.test_methods[0]

            # test runs successful
            self.assertIsNotNone(test_method.run())

    @parameterized.expand([
        ('html_sample_request',),
        ('zipped_html_sample_request',),
    ])
    @mock.patch('src.chain_smoker.api_client.APIClient.get')
    def test_can_use_built_config_html(self, request_name, get_mock):
        sample_request = getattr(self, request_name)
        get_mock.return_value = mock.Mock(
            json=mock.Mock(return_value={'foo': 1, 'bar': 'xxxxxx'}),
            status_code=200
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            # you can e.g. create a file here:
            temp_file_path = os.path.join(temp_dir, 'someFile.yaml')
            writer = TestFileWriter(sample_request, temp_file_path)

            config = writer._build_config()
            test_method = config['tests'][0]

            self.assertIsInstance(test_method.get('contains'), str)

    @parameterized.expand([
        ({'/get/': {'get': {'ignore_response': ['bar']}}}, {'foo': 1}),
        ({'/get/': {'get': {'ignore_response': ['unknown-key']}}}, {'foo': 1, 'bar': 'xxxxxx'}),
        ({'/get/': {'get': {'ignore_response': ['bar']}}}, {'foo': 1}),
        ({'/get/': {'get': {'ignore_response': ['bar']}}}, {'foo': 1}),
        ({'/get/': {'get': {}}}, {'foo': 1, 'bar': 'xxxxxx'}),
        ({'/get/': {}}, {'foo': 1, 'bar': 'xxxxxx'}),
        ({}, {'foo': 1, 'bar': 'xxxxxx'}),
    ])
    @mock.patch('src.chain_smoker.api_client.APIClient.get')
    def test_clean_response(self, request_config, expected_response, get_mock):
        get_mock.return_value = mock.Mock(
            json=mock.Mock(return_value={'foo': 1, 'bar': 'xxxxxx'}),
            status_code=200
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            # you can e.g. create a file here:
            temp_file_path = os.path.join(temp_dir, 'someFile.yaml')
            writer = TestFileWriter(self.sample_request, temp_file_path)

            writer.config.requests = request_config
            config = writer._build_config()
            test = config.get('tests')[0]

            self.assertDictEqual(test.get('contains'), expected_response, test)

    @parameterized.expand([
        ({}, {'foo': 1, 'bar': 'xxxxxx'}),
        ({'/post/': {'post': {}}}, {'foo': 1, 'bar': 'xxxxxx'}),
        ({'/post/': {'post': {'payload': {'unknown-key': 'yyyyyy'}}}}, {'foo': 1, 'bar': 'xxxxxx'}),
        ({'/post/': {'post': {'payload': {'foo': 1, 'bar': 'yyyyyy'}}}}, {'foo': 1, 'bar': 'yyyyyy'}),
        ({'/post/': {'post': {'payload': {'foo': 2}}}}, {'foo': 2, 'bar': 'xxxxxx'}),
    ])
    def test_clean_payload(self, request_config, expected_response):
        with tempfile.TemporaryDirectory() as temp_dir:
            # you can e.g. create a file here:
            temp_file_path = os.path.join(temp_dir, 'someFile.yaml')
            writer = TestFileWriter(self.post_sample_request, temp_file_path)

            writer.config.requests = request_config
            config = writer._build_config()
            test = config.get('tests')[0]

            self.assertDictEqual(test.get('payload'), expected_response, test)


class RewriteConfigTestCase(TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.sample_config = {
            'skip': {},
            'request': {},
            'headers': {},
            'skip_files': []
        }

    def test_from_file_unknown_file(self):
        config = RewriteConfig.from_file('foo')
        self.assertDictEqual(config.dict(), {'skip': {}, 'requests': {}, 'headers': {}, 'skip_files': []})

    def test_from_file_known_invalid_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_file_path = os.path.join(temp_dir, 'someFile.yaml')

            with open(temp_file_path, 'w') as file:
                yaml.dump(self.sample_config, file)

            config = RewriteConfig.from_file(temp_file_path)
            self.assertDictEqual(config.dict(), {'skip': {}, 'requests': {}, 'headers': {}, 'skip_files': []})

    @parameterized.expand([
        ({}, 'ignore_response', False, False, {}),
        ({'foo': 'bar'}, 'ignore_response', False, False, {}),
        ({'foo': 'bar', 'bar': 'baz'}, 'ignore_response', False, False, {'bar': 'baz'}),
        ({}, 'payload', True, False, {}),
        ({'foo': 1, 'bar': 'baz'}, 'payload', True, False, {'foo': 'bar', 'bar': 'baz'}),
        ('<html><h2>Sub-Title</h2></html>', 'keep', False, True, []),
        ('<html><h1>Title</h1></br><h2>Sub-Title</h2></html>', 'keep', False, True, ['Title']),
        (
            '<html><h1>Title</h1></br><h2>Sub-Title</h2><h1>Heading</h1></html>',
            'keep',
            False,
            True,
            ['Title', 'Heading']
        ),
    ])
    def test_apply(self, dict_value, conf_key, replace, regex_replace, expected_value):
        config_dict = dict(
            skip={},
            skip_files=[],
            requests={
                '/get/': {
                    'get': {
                        'ignore_response': ['foo'],
                        'payload': {
                            'foo': 'bar'
                        },
                        'keep': [r'<h1[^>]?>(\w+)?<\/h1[^>]?>'],
                    }
                }
            },
            headers={}
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_config_file_path = os.path.join(temp_dir, 'someConfigFile.yaml')
            temp_file_path = os.path.join(temp_dir, 'someFile.yaml')

            with open(temp_config_file_path, 'w') as file:
                yaml.dump(config_dict, file)

            writer = TestFileWriter({
                'Request': {
                    'Method': 'get', 'Path': 'https://example.com/get/', 'Payload': {},
                    'Protocol': 'HTTP/1', 'Headers': {},
                },
                'Response': {
                    'Status_code': 200, 'Body': {'foo': 1, 'bar': 'xxxxxx'}, 'Headers': {},
                }
            }, temp_file_path, temp_config_file_path)
            config = writer.config
        if isinstance(dict_value, str):
            method = self.assertEqual
        else:
            method = self.assertDictEqual

        method(
            config.apply(
                request=writer.request,
                obj=dict_value,
                conf_key=conf_key,
                replace=replace,
                regex_replace=regex_replace
            ),
            expected_value)

import os
import tempfile
from unittest import TestCase, mock

from pydantic import ValidationError

from src.chain_smoker.file_loader import TestFileLoader
from src.parser.file_writer import TestFileWriter


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
                'Status_code': 200, 'Body': {}, 'Headers': {},
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
        self.assertEqual(method.payload, {})
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

    @mock.patch('src.chain_smoker.api_client.APIClient.get')
    def test_can_use_built_config(self, get_mock):
        get_mock.return_value = mock.Mock(
            json=mock.Mock(return_value={}),
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

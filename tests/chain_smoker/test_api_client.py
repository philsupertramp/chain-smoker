from unittest import TestCase, mock
from parameterized import parameterized

from src.chain_smoker.api_client import APIClient, PayloadType
from src.chain_smoker.config import ClientConfig, AuthHeaderTemplate, AuthHeader


class APIClientTestCase(TestCase):
    def setUp(self) -> None:
        self.client = APIClient(ClientConfig(base_url='https://example.com/foo/'))
        self.client.session = mock.Mock()

    @parameterized.expand([
        ('bar/', 'https://example.com/foo/bar/'),
        ('bar/baz/', 'https://example.com/foo/bar/baz/'),
        ('/bar', 'https://example.com/bar'),
        ('/bar/baz/', 'https://example.com/bar/baz/'),

    ])
    def test_build_url(self, input_value, expected_url):
        self.assertEqual(self.client._build_url(input_value), expected_url)

    def test_auth_header_set_when_auth_header_passed(self):
        expected_value = 'bar'
        config = ClientConfig(
            base_url='https://example.com',
            auth_header=AuthHeaderTemplate(auth_header=AuthHeader(Authorization=expected_value))
        )
        client = APIClient(config)

        self.assertIn('Authorization', client.session.headers)
        self.assertEqual(client.session.headers.get('Authorization'), expected_value)

        client = APIClient(ClientConfig(base_url='https://example.com'))

        self.assertIsNotNone(client.session.headers)
        self.assertNotIn('Authorization', client.session.headers)

    @mock.patch('requests.Session.get')
    def test__request(self, get_mock):
        self.client._request('get', 'foo', False)

        get_mock.assert_called_once_with('https://example.com/foo/foo')

        self.client._request('get', 'foo', True)

        self.client.session.get.assert_called_once_with('https://example.com/foo/foo')

    def test__request_with_payload(self):
        request_mock = mock.Mock()
        self.client._request = request_mock

        self.client._request_with_payload('post', 'foo', {'foo': 'bar'}, PayloadType.JSON)

        request_mock.assert_called_once_with('post', 'foo', json={'foo': 'bar'})

        request_mock.reset_mock()

        self.client._request_with_payload('post', 'foo', {'foo': 'bar'}, PayloadType.MULTIPART)

        request_mock.assert_called_once_with('post', 'foo', data={'foo': 'bar'})

        request_mock.reset_mock()

        self.client._request_with_payload('post', 'foo', {'foo': 'bar'})

        request_mock.assert_called_once_with('post', 'foo', json={'foo': 'bar'})

        request_mock.reset_mock()

    def test_get(self):
        self.client.get('foo')

        self.client.session.get.assert_called_once()

    def test_post(self):
        self.client.post('foo', {'foo': 'bar'})

        self.client.session.post.assert_called_once()

    def test_put(self):
        self.client.put('foo', {'foo': 'bar'})

        self.client.session.put.assert_called_once()

    def test_patch(self):
        self.client.patch('foo', {'foo': 'bar'})

        self.client.session.patch.assert_called_once()

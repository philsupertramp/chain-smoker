import os
from unittest import TestCase, mock

from pydantic import ValidationError

from src.chain_smoker.config import TestCaseConfig, TestFileConfig, ClientConfig, TestConfig


class ConfigTestCase(TestCase):
    constructor = None

    def test_empty_dict(self):
        with self.assertRaises(ValidationError):
            self.constructor.from_dict({})


class TestCaseConfigTestCase(ConfigTestCase):
    constructor = TestCaseConfig

    def test_from_dict(self):
        with self.assertRaises(ValidationError):
            self.constructor.from_dict({})

        with self.assertRaises(ValidationError):
            self.constructor.from_dict({'type': 'api-test', 'config': {}, 'tests': {}})

        config = self.constructor.from_dict({
            'type': 'api-test',
            'config': {
                'client': {'base_url': 'example.com'}
            },
            'tests': {}
        })
        self.assertEqual(config.type, 'api-test')


class TestFileConfigTestCase(ConfigTestCase):
    constructor = TestFileConfig

    def test_from_dict_client_only(self):
        config = self.constructor.from_dict({'client': {'base_url': 'example.com'}})

        self.assertEqual(config.client.base_url, 'example.com')

    @mock.patch.dict(os.environ, {'bar': 'baz'})
    def test_from_dict_with_env(self):
        config = self.constructor.from_dict({'client': {'base_url': 'example.com'}, 'env': {'foo': 'bar'}})

        self.assertEqual(config.env[0].internal_key, 'foo')
        self.assertEqual(config.env[0].external_key, 'bar')

    def test_from_dict_with_env_unset_error(self):
        with self.assertRaises(ValidationError):
            self.constructor.from_dict({'client': {'base_url': 'example.com'}, 'env': {'foo': 'bar'}})

        with self.assertRaises(ValidationError):
            self.constructor.from_dict({'client': {'base_url': 'example.com'}, 'env': {None: 'bar'}})

        with self.assertRaises(ValidationError):
            self.constructor.from_dict({'client': {'base_url': 'example.com'}, 'env': {'foo': None}})


class ClientConfigTestCase(ConfigTestCase):
    constructor = ClientConfig

    def test_from_dict(self):
        config = self.constructor.from_dict({'base_url': 'https://example.com'})
        self.assertEqual(config.base_url, 'https://example.com')
        self.assertIsNone(config.auth_header)

        config = self.constructor.from_dict({
            'base_url': 'https://example.com',
            'auth_header': {'Authorization': 'Bearer Foo'}
        })
        self.assertEqual(config.base_url, 'https://example.com')
        self.assertIsNotNone(config.auth_header)
        self.assertIsNotNone(config.auth_header.auth_header)
        self.assertEqual(config.auth_header.auth_header.Authorization, 'Bearer Foo')


class TestConfigTestCase(ConfigTestCase):
    constructor = TestConfig

    def test_from_dict(self):
        config = self.constructor.from_dict({'name': 'name'})

        self.assertEqual(config.name, 'name')
        self.assertTrue(config.requires_auth)
        self.assertFalse(config.is_authentication)
        self.assertFalse(config.multi_step)

        with self.assertRaises(ValidationError):
            self.constructor.from_dict({'name': 'name', 'multi_step': True})
        self.constructor.from_dict({'name': 'name', 'multi_step': True, 'steps': [{'name': '1'}]})

        self.constructor.from_dict({'name': 'name', 'multi_step': False})
        self.constructor.from_dict({'name': 'name', 'is_authentication': False})
        with self.assertRaises(ValidationError):
            self.constructor.from_dict({'name': 'name', 'is_authentication': True})
        with self.assertRaises(ValidationError):
            self.constructor.from_dict({'name': 'name', 'is_authentication': True, 'payload': '{}'})
        with self.assertRaises(ValidationError):
            self.constructor.from_dict({
                'name': 'name',
                'is_authentication': True,
                'payload': '{}',
                'auth_header_template': {
                    'token_position': 'res.json().get("token")'
                }
            })
        with self.assertRaises(ValidationError):
            self.constructor.from_dict({
                'name': 'name',
                'is_authentication': True,
                'payload': '{}',
                'auth_header_template': {'auth_header': {'Authorization': 'Bearer {token}'}}
            })

        self.constructor.from_dict({
            'name': 'name',
            'is_authentication': True,
            'payload': '{}',
            'auth_header_template': {
                'token_position': 'res.json().get("token")', 'auth_header': {'Authorization': 'Bearer {token}'}
            }
        })


# remove template class
del ConfigTestCase

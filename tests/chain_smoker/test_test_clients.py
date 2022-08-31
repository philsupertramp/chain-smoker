from unittest import TestCase, mock

from parameterized import parameterized
from requests.cookies import RequestsCookieJar, create_cookie

from src.chain_smoker.api_client import APIClient
from src.chain_smoker.config import TestConfig, ClientConfig, AuthHeader, AuthHeaderTemplate, Cookie
from src.chain_smoker.test_clients import SmokeTest, ChainedSmokeTest


class SmokeTestTestCase(TestCase):
    def setUp(self) -> None:
        super().setUp()

    @staticmethod
    def create_test(name, method, endpoint, payload=None, uses=None,
                    requires_auth=True, expected_status_code=200, expected=None,
                    contains=None, contains_not=None, response_cookies=None):
        client_mock = mock.Mock()
        return SmokeTest(name=name, client=client_mock, method=method, endpoint=endpoint,
                         payload=payload, uses=uses, requires_auth=requires_auth,
                         expected_result=expected, contains_result=contains, expects_status_code=expected_status_code,
                         contains_not_result=contains_not, response_cookies=response_cookies)

    def test_build(self):
        client = APIClient(ClientConfig(base_url='example.com'))
        name = 'Name'
        config = TestConfig(name=name)

        test = SmokeTest.build(config, client)

        self.assertEqual(test.client, client)
        self.assertEqual(test.name, name)

    def test_get_response(self):
        test = self.create_test('test', 'get', 'example.com/')

        test._get_response()

        test.client.get.assert_called_with('example.com/', requires_auth=True)

    def test_get_response_with_uses(self):
        test = self.create_test('test', 'get', 'example.com/', uses={'key': 'values.get("value")'})

        test._get_response()

        test.client.get.assert_called_with('example.com/', requires_auth=True)

        test = self.create_test('test', 'get', 'example.com/{key}', uses={'key': 'values.get("value")'})

        test._get_response(values={'value': 'endpoint'})

        test.client.get.assert_called_with('example.com/endpoint', requires_auth=True)

        test = self.create_test(
            'test', 'post', 'example.com/{key}', payload="{'foo': '{key}'}", uses={'key': 'values.get("value")'}
        )

        test._get_response(values={'value': 'endpoint'})

        test.client.post.assert_called_with('example.com/endpoint', {'foo': 'endpoint'}, requires_auth=True)

    @parameterized.expand([
        (mock.Mock(text='Foo   .     bar', json=mock.Mock(side_effect=ValueError)), 'Foo .  bar'),
        (mock.Mock(text='Foo  bar', json=mock.Mock(side_effect=ValueError)), 'Foo bar'),
        (mock.Mock(json=mock.Mock(return_value={'key': 'value'})), {'key': 'value'}),
    ])
    def test_get_response_content(self, res_mock, expected_output):
        out = SmokeTest._get_response_content(res_mock)
        if isinstance(expected_output, dict):
            self.assertDictEqual(out, expected_output)
        else:
            self.assertEqual(out, expected_output)

    def test_run_status_code(self):
        test = self.create_test('test', 'get', 'example.com/')
        test.client.get.return_value = mock.Mock(status_code=200, json=mock.Mock(return_value={'key': 'value'}))
        res = test.run()
        self.assertIsNotNone(res)

        test = self.create_test('test', 'get', 'example.com/')
        test.client.get.return_value = mock.Mock(status_code=500, json=mock.Mock(return_value={'key': 'value'}))
        res = test.run()
        self.assertIsNone(res)

    def test_run_expected(self):
        test = self.create_test('test', 'get', 'example.com/', expected={'key': 'value'})
        test.client.get.return_value = mock.Mock(status_code=200, json=mock.Mock(return_value={'key': 'value'}))
        res = test.run()
        self.assertIsNotNone(res)

        test = self.create_test('test', 'get', 'example.com/', expected={'foo': 'value'})
        test.client.get.return_value = mock.Mock(status_code=200, json=mock.Mock(return_value={'key': 'value'}))
        res = test.run()
        self.assertIsNone(res)

    def test_run_contains(self):
        test = self.create_test('test', 'get', 'example.com/', contains={'key': 'value'})
        test.client.get.return_value = mock.Mock(status_code=200, json=mock.Mock(return_value={'key': 'value'}))
        res = test.run()
        self.assertIsNotNone(res)

        test = self.create_test('test', 'get', 'example.com/', contains={'foo': 'value'})
        test.client.get.return_value = mock.Mock(status_code=200, json=mock.Mock(return_value={'key': 'value'}))
        res = test.run()
        self.assertIsNone(res)

    def test_run_contains_not(self):
        test = self.create_test('test', 'get', 'example.com/', contains_not={'key': 'value'})
        test.client.get.return_value = mock.Mock(status_code=200, json=mock.Mock(return_value={'key': 'value'}))
        res = test.run()
        self.assertIsNone(res)

        test = self.create_test('test', 'get', 'example.com/', contains_not={'foo': 'value'})
        test.client.get.return_value = mock.Mock(status_code=200, json=mock.Mock(return_value={'key': 'value'}))
        res = test.run()
        self.assertIsNotNone(res)

    def test_run_contains_cookies(self):
        test = self.create_test('test', 'get', 'example.com/', response_cookies=[Cookie(key='bar', domain='example.com')])

        jar = RequestsCookieJar()
        jar.set_cookie(
            create_cookie(name='foo', domain='example.com', value='2')
        )
        test.client.get.return_value = mock.Mock(
            status_code=200, json=mock.Mock(return_value={'key': 'value'}), cookies=jar
        )
        res = test.run()
        self.assertIsNone(res)

        test = self.create_test(
            'test', 'get', 'example.com/', response_cookies=[Cookie(key='foo', domain='example.com')]
        )
        test.client.get.return_value = mock.Mock(
            status_code=200, json=mock.Mock(return_value={'key': 'value'}), cookies=jar
        )
        res = test.run()
        self.assertIsNotNone(res)


class ChainedSmokeTestTestCase(TestCase):
    def test_build(self):
        client = APIClient(ClientConfig(base_url='example.com'))
        name = 'Name'
        config = TestConfig(name=name)

        test = ChainedSmokeTest.build(config, client)

        self.assertEqual(test.client, client)
        self.assertEqual(test.name, name)

    def test_build_test(self):
        client = mock.Mock()
        name = 'Name'
        test_1 = TestConfig(name='test_1')
        test_2 = TestConfig(
            name='test_2', is_authentication=True, payload='{}',
            auth_header_template=AuthHeaderTemplate(
                auth_header=AuthHeader(Authorization='Barer foo'),
                token_position='res.json().get(\'token\')'
            )
        )
        config = TestConfig(
            name=name,
            steps=[
                test_1, test_2
            ]
        )

        test = ChainedSmokeTest.build(config, client)

        self.assertEqual(test.client, client)
        self.assertEqual(test.name, name)
        self.assertEqual(test.steps, [test_1, test_2])

        client.get.return_value = mock.Mock(json=mock.Mock(return_value={'token': 'XXXXX'}))

        test._build_test()

        self.assertEqual(test.tests['test_1'].name, 'test_1')
        self.assertNotIn('test_2', test.tests)

        self.assertIsNotNone(test.values['test_2'])
        self.assertDictEqual(test.values['test_2'], {'token': 'XXXXX'})

    def test_run(self):
        client = mock.Mock()
        name = 'Name'
        test_1 = TestConfig(name='test_1')
        test_2 = TestConfig(
            name='test_2', is_authentication=True, payload='{}',
            auth_header_template=AuthHeaderTemplate(
                auth_header=AuthHeader(Authorization='Barer foo'),
                token_position='res.json().get(\'token\')'
            )
        )
        config = TestConfig(
            name=name,
            steps=[
                test_1, test_2
            ]
        )
        test = ChainedSmokeTest.build(config, client)
        client.get.return_value = mock.Mock(json=mock.Mock(return_value={'token': 'XXXXX'}))

        test._build_test()

        test.run()

        self.assertIsNotNone(test.values['test_1'])
        self.assertDictEqual(test.values['test_1'], {'token': 'XXXXX'})
        self.assertIsNotNone(test.values['test_2'])
        self.assertDictEqual(test.values['test_2'], {'token': 'XXXXX'})

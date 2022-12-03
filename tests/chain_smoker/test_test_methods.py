from datetime import timedelta, datetime
from time import strptime
from unittest import TestCase, mock

from parameterized import parameterized
from requests.cookies import RequestsCookieJar, create_cookie

from src.chain_smoker.config import Cookie
from src.chain_smoker.test_methods import ExpectedTest, ExpectedStatusCodeTest, ContainsTest, ContainsCookiesTest


class ExpectedTestTestCase(TestCase):
    @parameterized.expand([
        (1, 1, True),
        (1, 2, False),
        (1, '1', False),
        ('foo', 'foo', True),
        ('foo', 'bar', False),
        ({'id': 1}, {'id': 1}, True),
        ({'id': 1}, {'id': 2}, False),
    ])
    def test_run_test(self, input_value, other_value, expected_result):
        self.assertEqual(ExpectedTest(input_value, '', '').test(other_value), expected_result)


class ExpectedStatusCodeTestTestCase(TestCase):
    @parameterized.expand([
        (200, mock.Mock(status_code=200), True),
        (200, mock.Mock(status_code=400), False),
    ])
    def test_run_test(self, input_value, other_value, expected_result):
        self.assertEqual(ExpectedStatusCodeTest(input_value, '', '').test(other_value), expected_result)

    @parameterized.expand([
        (200, mock.Mock(status_code=200), False),
        (200, mock.Mock(status_code=400), True),
    ])
    def test_run_test_inverse(self, input_value, other_value, expected_result):
        self.assertEqual(ExpectedStatusCodeTest(input_value, '', '', inverse=True).test(other_value), expected_result)


class ContainsTestTestCase(TestCase):
    @parameterized.expand([
        ('Foo bar', 'The story of Foo bar is extremely important to remember', True),
        ('Baz', 'The story of Foo bar is extremely important to remember', False),
        ({'text': 'Foo bar'}, {'text': 'Foo bar'}, True),
        ({'text': 'Foo bar'}, {'id': 1, 'text': 'Foo bar'}, True),
        ({'id': 1, 'text': 'Foo bar'}, {'text': 'Foo bar'}, False),
        ({'foo': 'bar'}, {'foo': 'baz'}, False),
        ({'foo': 'bar'}, {'id': 1, 'text': 'Foo bar'}, False),
        ({'nested_obj': {'id': 1, 'field': 'name'}}, {'nested_obj': {'id': 1, 'field': 'name'}}, True),
        ({'nested_obj': {'id': 1, 'field': 'name'}}, {'nested_obj': {'id': 1, 'field': 'name-2'}}, False),
        ({'nested_obj': {'id': 1, 'field': 'name'}}, {'nested_obj': {'address': 'name'}}, False),
        ({'baz': {'id': 1, 'field': 'name'}}, {'nested_obj': {'id': 1, 'field': 'name'}}, False),
        ({'id': 1}, [{'id': 1}], True),
        ({'id': 1}, [{'id': 2}], False),
        (1, [1, 2, 3], True),
        (4, [1, 2, 3], False),
        ({'payload': 1}, {'payload': [1, 2, 3]}, True),
        ({'payload': 4}, {'payload': [1, 2, 3]}, False),
        (['foo', 'bar'], {'foo': 1, 'bar': 2, 'baz': 3}, True),
        (['foo'], {'foo': 1, 'bar': 2}, True),
        (['baz'], {'foo': 1, 'bar': 2}, False),
    ])
    def test_run_test(self, input_value, other_value, expected_result):
        self.assertEqual(ContainsTest(input_value, '', '').test(other_value), expected_result)

    @parameterized.expand([
        ('Foo bar', 'The story of Foo bar is extremely important to remember', False),
        ('Baz', 'The story of Foo bar is extremely important to remember', True),
        ({'text': 'Foo bar'}, {'text': 'Foo bar'}, False),
        ({'text': 'Foo bar'}, {'id': 1, 'text': 'Foo bar'}, False),
        ({'id': 1, 'text': 'Foo bar'}, {'text': 'Foo bar'}, False),
        ({'foo': 'bar'}, {'foo': 'baz'}, True),
        ({'foo': 'bar'}, {'id': 1, 'text': 'Foo bar'}, True),
        ({'nested_obj': {'id': 1, 'field': 'name'}}, {'nested_obj': {'id': 1, 'field': 'name'}}, False),
        ({'nested_obj': {'id': 1, 'field': 'name'}}, {'nested_obj': {'address': 'name'}}, True),
        ({'id': 1}, [{'id': 1}], False),
        ({'id': 1}, [{'id': 2}], True),
        (1, [1, 2, 3], False),
        (4, [1, 2, 3], True),
        ({'payload': 1}, {'payload': [1, 2, 3]}, False),
        ({'payload': 4}, {'payload': [1, 2, 3]}, True),
        (['foo', 'bar'], {'foo': 1, 'bar': 2, 'baz': 3}, False),
        (['foo'], {'foo': 1, 'bar': 2}, False),
        (['baz'], {'foo': 1, 'bar': 2}, True),
    ])
    def test_run_test_inverse(self, input_value, other_value, expected_result):
        self.assertEqual(ContainsTest(input_value, '', '', inverse=True).test(other_value), expected_result)


class ContainsCookiesTestTesCase(TestCase):
    @parameterized.expand([
        (dict(key='foo', domain='example.com'), dict(name='foo', domain='example.com', value='2'), True),
        (dict(key='foo', domain='example.com', value='2'), dict(name='foo', domain='example.com', value='2'), True),
        (dict(key='foo', domain='example.com', value='3'), dict(name='foo', domain='example.com', value='2'), False),
        (dict(key='foo', domain='foo.com'), dict(name='foo', domain='example.com', value='2'), False),
        (dict(key='foo', domain='example.com'), dict(name='foo', domain='foo.com', value='2'), False),
        (dict(key='foo', domain='example.com'), dict(name='bar', domain='example.com', value='2'), False),
        (
            dict(key='foo', domain='example.com', value='2', max_age='5m'),
            dict(
                name='foo',
                value='2',
                domain='example.com',
                expires=(datetime.now() + timedelta(minutes=5)).timestamp()
            ),
            True
        ),
        (
            dict(key='foo', domain='example.com', value='2', max_age='5m'),
            dict(
                name='foo',
                value='2',
                domain='example.com',
                expires=(datetime.now() + timedelta(minutes=5)).timestamp()
            ),
            True
        ),
        (
            dict(key='foo', domain='example.com', value='2', max_age='5m'),
            dict(
                name='foo',
                value='2',
                domain='example.com',
                expires=(datetime.now() + timedelta(minutes=6)).timestamp()
            ),
            False
        ),
        (
            dict(key='foo', domain='example.com', value='2', max_age='session'),
            dict(
                name='foo',
                value='2',
                domain='example.com',
                expires=(datetime.now() + timedelta(minutes=5)).timestamp()
            ),
            False
        ),
        (
            dict(key='foo', domain='example.com', value='2', max_age='5m'),
            dict(name='foo', value='2', domain='example.com', expires=None),
            False
        ),
        (
            dict(key='foo', domain='example.com', value='2', max_age='Session'),
            dict(name='foo', value='2', domain='example.com', expires=None),
            True
        ),
        (
            dict(key='foo', domain='example.com', value='2', max_age='session'),
            dict(name='foo', value='2', domain='example.com', expires=None),
            True
        ),
    ])
    def test_run_test(self, test_cookie_conf, response_cookie_conf, expected_result):
        test = ContainsCookiesTest([Cookie(**test_cookie_conf)], '', '')
        jar = RequestsCookieJar()
        if response_cookie_conf is not None:
            jar.set_cookie(
                create_cookie(**response_cookie_conf)
            )
        self.assertEqual(test.test(jar), expected_result)

    def test_run_test_inverse(self):
        test = ContainsCookiesTest([Cookie(key='foo', domain='example.com', value='2')], '', '', inverse=True)
        with self.assertRaises(NotImplementedError):
            test.test({})

    @parameterized.expand([
        ('Session', 'session'),
        ('session', 'session'),
        ('5m', timedelta(minutes=5)),
        ('5W', timedelta(weeks=5)),
        ('5M', timedelta(weeks=4*5)),
        ('5D', timedelta(days=5)),
        ('5d', timedelta(days=5)),
    ])
    def test_get_max_age(self, input_value, expected_output_value):
        now = datetime.now()
        cookie = Cookie(key='foo', domain='example.com', max_age=input_value)

        if not isinstance(expected_output_value, str):
            expected_output_value = now + expected_output_value

        with mock.patch('src.chain_smoker.test_methods.datetime', create=True) as now_mock:
            now_mock.timedelta = timedelta
            now_mock.datetime.strptime = strptime
            now_mock.datetime.now.return_value = now
            self.assertEqual(ContainsCookiesTest([cookie], '', '')._get_max_age(cookie), expected_output_value)

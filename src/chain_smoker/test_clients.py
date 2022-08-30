import datetime
from collections import OrderedDict
from typing import Union, Dict, List, Optional
from functools import partial

from requests import Response
from requests.cookies import RequestsCookieJar

from .api_client import APIClient
from .config import TestConfig, Cookie
from .logger import logger
from .mixins import ExpectedMixin


TestValueType = Union[Dict, str, int, List[Cookie], Response, RequestsCookieJar]


class ValueTest:
    """
    Base test class handles comparison of received values with expected values
    """
    def __init__(self, value: TestValueType, inverse=False):
        self.value = value
        self.inverse = inverse

    def _run_test(self, other_value: TestValueType, name: str, method: str) -> None:
        raise NotImplementedError()

    def test(self, other_value: Union[Dict, str, int, Response, RequestsCookieJar], name: str, method: str) -> bool:
        self.error = ''
        self.found_error = False
        self._run_test(other_value, name, method)
        if self.found_error:
            logger.error(self.error)
        return not self.found_error


class ExpectedTest(ValueTest):
    """
    Equal comparison of objects
    """
    def _run_test(self, other_value: TestValueType, name: str, method: str) -> None:
        op = '__eq__' if self.inverse else '__ne__'
        if getattr(other_value, op)(self.value):
            self.error = f'Unexpected result for {name}!\n{other_value}\n'
            self.error += '==' if self.inverse else '!='
            self.error += f'\n{self.value}\n{method}'
            self.found_error = True


class ExpectedStatusCodeTest(ValueTest):
    """
    Equal comparison of objects
    """
    def _run_test(self, other_value: Response, name: str, method: str) -> None:
        op = '__eq__' if self.inverse else '__ne__'
        if getattr(other_value.status_code, op)(self.value):
            self.error = f'Unexpected status_code for {name}!\n{other_value.status_code}\n'
            self.error += '==' if self.inverse else '!='
            self.error += f'\n{self.value}\n{method}'
            self.found_error = True


class ContainsTest(ValueTest):
    """
    Tests if value member of received value.

    - string/integer: Expected value part of received value (Expected IN Received)
    - dictionary: Expected (key, value)-pairs are within received values
    """
    def _run_test(self, other_value: TestValueType, name: str, method: str) -> None:
        if self.inverse:
            self._run_negative_test(other_value, name, method)
        else:
            self._run_positive_test(other_value, name, method)

    def _run_negative_test(self, other_value: TestValueType, name: str, method: str) -> None:
        if isinstance(self.value, (str, int)):
            if self.value in other_value:
                self.error = f'Unexpected result for {name}!\n' \
                             f'{self.value}  in:\n' \
                             f'{other_value}'
                self.found_error = True
                return
        else:
            for key, value in self.value.items():
                if isinstance(value, dict):
                    for nested_key, nested_value in value.items():
                        if nested_key in other_value[key]:
                            self.error = f'Unexpected result for {name}!\n' \
                                         f'{nested_key} found in:\n' \
                                         f'{other_value[key]}'
                            self.found_error = True
                            return
                else:
                    if key in other_value and other_value[key] == value:
                        self.error = f'Unexpected result for {name}!\n{other_value[key]}=={value}\n{method}'
                        self.found_error = True

    def _run_positive_test(self, other_value: TestValueType, name: str, method: str) -> None:
        if isinstance(self.value, (str, int)):
            if self.value not in other_value:
                self.error = f'Unexpected result for {name}!\n' \
                             f'{self.value} not found in:\n' \
                             f'{other_value}'
                self.found_error = True
                return
        elif isinstance(self.value, dict):
            for key, value in self.value.items():
                if isinstance(value, dict):
                    for nested_key, nested_value in value.items():
                        if nested_key not in other_value[key]:
                            self.error = f'Unexpected result for {name}!\n' \
                                         f'{nested_key} not found in:\n' \
                                         f'{other_value[key]}'
                            self.found_error = True
                            return
                        if other_value[key][nested_key] != nested_value:
                            self.error = f'Unexpected result for {name}!\n' \
                                         f'{other_value[key][nested_key]}!={nested_value}\n' \
                                         f'{method}'
                            self.found_error = True
                            return
                else:
                    if key not in other_value:
                        self.error = f'Unexpected result for {name}!\n{key} not found in:\n{other_value}'
                        self.found_error = True
                        return
                    if other_value[key] != value:
                        self.error = f'Unexpected result for {name}!\n{other_value[key]}!={value}\n{method}'
                        self.found_error = True
                        return
        else:
            raise NotImplementedError()


class ContainsCookiesTest(ValueTest):
    def _get_max_age(self, cookie: Cookie) -> Union[str, datetime.datetime]:
        if cookie.max_age.lower() == 'session':
            return 'session'
        try:
            max_age = datetime.datetime.strptime(cookie.max_age, "%Y-%m-%dT%H:%M:%S%z").timestamp()
        except ValueError:
            if cookie.max_age[-1] == 'm':
                max_age = datetime.datetime.now() + datetime.timedelta(minutes=int(cookie.max_age[:-1]))
            elif cookie.max_age[-1].lower() == 'd':
                max_age = datetime.datetime.now() + datetime.timedelta(days=int(cookie.max_age[:-1]))
            elif cookie.max_age[-1] == 'M':
                max_age = datetime.datetime.now() + datetime.timedelta(weeks=4 * int(cookie.max_age[:-1]))
            elif cookie.max_age[-1] == 'W':
                max_age = datetime.datetime.now() + datetime.timedelta(weeks=int(cookie.max_age[:-1]))
            else:
                raise NotImplementedError('Value not supported.')
        return max_age

    def _run_test(self, other_value: TestValueType, name: str, method: str) -> None:
        if self.inverse:
            raise NotImplementedError()
        else:
            self._run_positive_test(other_value, name, method)

    def _run_positive_test(self, other_value: RequestsCookieJar, name: str, method: str) -> None:
        not_found = []
        for cookie in self.value:
            found = False
            for response_cookie in other_value:
                if response_cookie.name != cookie.key:
                    continue
                found = True
                if cookie.domain is not None and cookie.domain != response_cookie.domain:
                    self.error = 'Unexpected result for ' \
                                 f'{name}!\nDomain: {response_cookie.domain}!={cookie.domain}\n{method}'
                    self.found_error = True
                    return
                if cookie.value is not None and response_cookie.value != cookie.value:
                    self.error = 'Unexpected result for ' \
                                 f'{name}!\n{response_cookie.value}!={cookie.value}\n{method}'
                    self.found_error = True
                    return
                if cookie.max_age is not None:
                    max_age = self._get_max_age(cookie)
                    if max_age == 'session':
                        if response_cookie.expires is None:
                            continue
                        else:
                            self.error = f'Unexpected result for {name}!\n' \
                                         f'Received for cookie "{cookie.key}" expiration of ' \
                                         f'"{response_cookie.expires}", expected "session"'
                            self.found_error = True
                            return
                    elif response_cookie.expires is None:
                        self.error = f'Unexpected result for {name}!\n' \
                                     f'Received for cookie "{cookie.key}" expiration of ' \
                                     f'"session", expected "{cookie.max_age}"'
                        self.found_error = True
                        return
                    elif abs(max_age.timestamp() - response_cookie.expires) >= 30:
                        self.error = 'Unexpected result for ' \
                                     f'{name}!\n{response_cookie.expires}!={max_age}\n{method}'
                        self.found_error = True
                    return
            if not found:
                not_found.append(cookie.key)

        if not_found:
            self.error = f'Did not find cookies {", ".join(not_found)}'
            self.found_error = True
            return


class SmokeTest(ExpectedMixin):
    """
    Single test entity
    """
    def __init__(self, name: str, client: APIClient, method: str, endpoint: str,
                 payload: TestValueType, uses: Optional[Dict], requires_auth: Optional[bool] = True,
                 expects_status_code: Optional[int] = None, expected_result: Optional[TestValueType] = None,
                 contains_result: Optional[TestValueType] = None,
                 contains_not_result: Optional[TestValueType] = None,
                 response_cookies: Optional[List[Cookie]] = None) -> None:
        self.name: str = name
        self.client: APIClient = client
        self.method: str = method
        self.endpoint: str = endpoint
        self.payload: Optional[Union[Dict, str, int]] = payload
        self.uses: Optional[Dict] = uses
        self.requires_auth = requires_auth
        self.expected_result: ExpectedTest = ExpectedTest(expected_result) if expected_result else None
        self.contains_result: ContainsTest = ContainsTest(contains_result) if contains_result else None
        self.response_cookies: ContainsTest = ContainsCookiesTest(response_cookies) if response_cookies else None
        self.expects_status_code: ExpectedStatusCodeTest = ExpectedStatusCodeTest(expects_status_code) \
            if expects_status_code else None
        self.contains_not_result: ContainsTest = ContainsTest(contains_not_result, inverse=True) \
            if contains_not_result else None

    def _get_response(self, *args, **kwargs) -> Response:
        endpoint = self.endpoint
        payload = self.payload

        if self.uses is not None:
            values = kwargs.pop('values', {})
            format_values = {k: eval(v, {'values': values}) for k, v in self.uses.items()}
            endpoint = self.endpoint.format(**format_values)
            if payload:
                for key, value in format_values.items():
                    payload = payload.replace('{' + key + '}', value)

        kwargs.pop('values', None)
        if self.payload is not None:
            method = partial(getattr(self.client, self.method), endpoint, self.build_expected(payload))
        else:
            method = partial(getattr(self.client, self.method), endpoint)

        return method(requires_auth=self.requires_auth, *args, **kwargs)

    @staticmethod
    def _get_response_content(res: Response) -> TestValueType:
        try:
            return res.json()
        except ValueError:
            return res.text.replace('\n', '').replace('   ', ' ').replace('  ', ' ')

    def run(self, *args, **kwargs) -> Optional[TestValueType]:
        result = self._get_response(*args, **kwargs)
        if self.expects_status_code and not self.expects_status_code.test(result, self.name, self.method):
            return
        if self.response_cookies is not None and not self.response_cookies.test(result.cookies, self.name, self.method):
            return

        result = self._get_response_content(result)

        if self.expected_result is not None and not self.expected_result.test(result, self.name, self.method):
            return
        if self.contains_result is not None and not self.contains_result.test(result, self.name, self.method):
            return
        if self.contains_not_result is not None and not self.contains_not_result.test(result, self.name, self.method):
            return
        logger.info(f'Success for {self.name}!')
        return result

    @classmethod
    def build(cls, step: TestConfig, client: APIClient) -> 'SmokeTest':
        return cls(
            name=step.name,
            client=client,
            method=step.method,
            endpoint=step.endpoint,
            expects_status_code=step.expects_status_code,
            expected_result=step.expected,
            contains_result=step.contains,
            contains_not_result=step.contains_not,
            payload=step.payload,
            uses=step.uses,
            requires_auth=step.requires_auth,
            response_cookies=step.response_cookies,
        )


class ChainedSmokeTest(ExpectedMixin):
    """
    Chained test entity.

    Chained tests can reuse values of previous tests using the "uses" keyword.
    Additionally, an authentication step can be inserted, marked using the "is_authentication" keyword.
    """
    def __init__(self, name: str, steps: List[TestConfig], client: APIClient):
        self.name: str = name
        self.steps: List[TestConfig] = steps
        self.client: APIClient = client
        self.tests: Dict[str, SmokeTest] = dict()
        self.values = dict()

    def _build_test(self):
        tests = list()
        for step in self.steps:
            if step.is_authentication:
                # TODO: include "uses" here
                # NOTE: do NOT remove this assignment, `res` is a magic value for users
                res = getattr(self.client, step.method)(step.endpoint, data=self.build_expected(step.payload))
                auth_key, auth_value = list(step.auth_header_template.auth_header.dict().items())[0]
                auth_value = auth_value.format(token=eval(step.auth_header_template.token_position))
                self.client.session.headers = {auth_key: auth_value}
                self.values[step.name] = SmokeTest._get_response_content(res)
            else:
                tests.append(
                    (step.name, SmokeTest.build(step, self.client))
                )

        self.tests = OrderedDict(tests)

    def run(self):
        logger.info(f'Running chained test case {self.name}:')
        self.values = dict()
        self._build_test()
        for test_name, test in self.tests.items():
            self.values[test_name] = test.run(values=self.values)

    @classmethod
    def build(cls, step: TestConfig, client: APIClient) -> 'ChainedSmokeTest':
        return cls(step.name, step.steps, client)

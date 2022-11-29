from collections import OrderedDict
from typing import Union, Dict, List, Optional
from functools import partial

from requests import Response

from .api_client import APIClient
from .config import TestConfig, Cookie
from .logger import logger
from .mixins import EvaluationMixin
from .test_methods import TestValueType, ExpectedTest, ContainsTest, ContainsCookiesTest, ExpectedStatusCodeTest


class SmokeTest(EvaluationMixin):
    """
    Single test entity
    """
    def __init__(self, name: str, client: APIClient, method: str, endpoint: str,
                 payload: TestValueType, uses: Optional[Dict], requires_auth: Optional[bool] = True,
                 headers: Optional[Dict] = None, expects_status_code: Optional[int] = None,
                 expected_result: Optional[TestValueType] = None, contains_result: Optional[TestValueType] = None,
                 contains_not_result: Optional[TestValueType] = None, response_cookies: Optional[List[Cookie]] = None,
                 response_headers: Optional[Dict] = None, request_cookies: Optional[List[Cookie]] = None) -> None:
        self.name: str = name
        self.client: APIClient = client
        self.method: str = method
        self.endpoint: str = endpoint
        self.payload: Optional[Union[Dict, str, int]] = payload
        self.payload_cookies: Optional[List[Cookie]] = request_cookies
        self.uses: Optional[Dict] = uses
        self.requires_auth = requires_auth
        self.expected_result: ExpectedTest = ExpectedTest(
            expected_result, name=name, method=method
        ) if expected_result else None
        self.contains_result: ContainsTest = ContainsTest(
            contains_result, name=name, method=method
        ) if contains_result else None
        self.response_cookies: ContainsCookiesTest = ContainsCookiesTest(
            response_cookies, name=name, method=method
        ) if response_cookies else None
        self.expects_status_code: ExpectedStatusCodeTest = ExpectedStatusCodeTest(
            expects_status_code, name=name, method=method
        ) if expects_status_code else None
        self.contains_not_result: ContainsTest = ContainsTest(
            contains_not_result, inverse=True, name=name, method=method
        ) if contains_not_result else None
        self.headers = headers
        self.response_headers: ContainsTest = ContainsTest(
            response_headers, name=name, method=method
        ) if response_headers else None

    def _get_response(self, *args, **kwargs) -> Response:
        endpoint = self.endpoint
        payload = self.payload
        request_kwargs = {}

        env = kwargs.pop('env', {})
        if self.uses is not None:
            values = kwargs.pop('values', {})
            format_values = {k: eval(v, {'values': values, 'env': env}) for k, v in self.uses.items()}
            endpoint = self.endpoint.format(**format_values)
            if payload:
                for key, value in format_values.items():
                    payload = payload.replace('{' + key + '}', value)

        if self.payload_cookies is not None:
            request_kwargs.update({'cookies': {c.key: c.value for c in self.payload_cookies}})

        kwargs.pop('values', None)
        # set temporary headers
        self.client.set_headers(self.headers)

        if self.payload is not None:
            method = partial(
                getattr(self.client, self.method),
                endpoint,
                self.evaluate_value(payload),
                **request_kwargs
            )
        else:
            method = partial(getattr(self.client, self.method), endpoint, **request_kwargs)

        return method(requires_auth=self.requires_auth, *args, **kwargs)

    @staticmethod
    def _get_response_content(res: Response) -> TestValueType:
        try:
            return res.json()
        except ValueError:
            return res.content.decode('utf-8')

    def run(self, *args, **kwargs) -> Optional[TestValueType]:

        result = self._get_response(*args, **kwargs)

        if self.expects_status_code and not self.expects_status_code.test(result):
            return
        if self.response_cookies is not None and not self.response_cookies.test(result.cookies):
            return
        if self.response_headers is not None and not self.response_headers.test(result.headers):
            return

        result = self._get_response_content(result)

        if self.expected_result is not None and not self.expected_result.test(result):
            return
        if self.contains_result is not None and not self.contains_result.test(result):
            return
        if self.contains_not_result is not None and not self.contains_not_result.test(result):
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
            headers=step.headers,
            uses=step.uses,
            requires_auth=step.requires_auth,
            response_cookies=step.response_cookies,
            response_headers=step.response_headers,
            request_cookies=step.payload_cookies
        )


class ChainedSmokeTest(EvaluationMixin):
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
                res = getattr(self.client, step.method)(step.endpoint, data=self.evaluate_value(step.payload))
                auth_key, auth_value = list(step.auth_header_template.auth_header.dict().items())[0]
                auth_value = auth_value.format(token=eval(step.auth_header_template.token_position))
                auth_header = {auth_key: auth_value}
                self.client.session.headers = auth_header
                self.client.default_headers = auth_header.copy()
                self.values[step.name] = SmokeTest._get_response_content(res)
            else:
                tests.append(
                    (step.name, SmokeTest.build(step, self.client))
                )

        self.tests = OrderedDict(tests)

    def run(self, env=None):
        logger.info(f'Running chained test case {self.name}:')
        self.values = dict()
        self._build_test()
        for test_name, test in self.tests.items():
            self.values[test_name] = test.run(values=self.values, env=env)

    @classmethod
    def build(cls, step: TestConfig, client: APIClient) -> 'ChainedSmokeTest':
        return cls(step.name, step.steps, client)

import datetime
from typing import Union, Dict, List

from requests import Response
from requests.cookies import RequestsCookieJar

from .config import Cookie
from .logger import logger

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

    def _test_key_in_value(self, key, other_value, name, method):
        if (key in other_value) == self.inverse:
            self.error = f'Unexpected result for {name}!\n' \
                         f'{key}{"" if self.inverse else " not"} found in:\n' \
                         f'{other_value}\n{method}'
            self.found_error = True
            return True
        return False

    def _test_exact_value(self, value, other_value, name, method):
        if (other_value == value) == self.inverse:
            self.error = f'Unexpected result for {name}!\n{value}' \
                         f'{"==" if self.inverse else "!="}{other_value}\n{method}'
            self.found_error = True
            return True
        return False


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
        if isinstance(self.value, (str, int)):
            if self._test_value(self.value, other_value, name, method):
                return
        elif isinstance(self.value, dict):
            if self._test_dict(self.value, other_value, name, method):
                return
        else:
            raise NotImplementedError()

    def _test_dict(self, value_in, other_value, name, method) -> bool:
        for key, value in value_in.items():
            if isinstance(value, dict):
                if key not in other_value and self._test_key_in_value(key, other_value, name, method):
                    return True
                return self._test_dict(value, other_value[key], name, method)
            else:
                if key in other_value:
                    if self._test_exact_value(value, other_value[key], name, method):
                        return True
                elif not self.inverse:
                    return self._test_key_in_value(key, other_value, name, method)

        return False

    def _test_value(self, value, other_value, name, method) -> bool:
        return self._test_key_in_value(value, other_value, name, method)


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

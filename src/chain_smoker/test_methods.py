import datetime
from typing import Union, Dict, List

from requests import Response
from requests.cookies import RequestsCookieJar
from requests.structures import CaseInsensitiveDict

from .config import Cookie
from .logger import logger

TestValueType = Union[Dict, str, int, List[Cookie], Response, RequestsCookieJar]


class ValueTest:
    """
    Base test class handles comparison of received values with expected values
    """
    def __init__(self, value: TestValueType, name: str, method: str, inverse=False):
        self.value = value
        self.inverse = inverse
        self.name = name
        self.method = method

    def _run_test(self, other_value: TestValueType) -> None:
        raise NotImplementedError()

    def test(self, other_value: Union[Dict, str, int, Response, RequestsCookieJar, CaseInsensitiveDict]) -> bool:
        self.error = ''
        self.found_error = False
        self._run_test(other_value)
        if self.found_error:
            if isinstance(self.error, list):
                for error in self.error:
                    logger.error(error)
            else:
                logger.error(self.error)
        return not self.found_error

    def _test_key_in_value(self, key, other_value):
        if (key in other_value) == self.inverse:
            self.error = f'Unexpected result for {self.name}!\n' \
                         f'{key}{"" if self.inverse else " not"} found in:\n' \
                         f'{other_value}\n{self.method}'
            self.found_error = True
            return True
        return False

    def _test_exact_value(self, value, other_value):
        if (other_value == value) == self.inverse:
            self.error = f'Unexpected result for {self.name}!\n{value}' \
                         f'{"==" if self.inverse else "!="}{other_value}\n{self.method}'
            self.found_error = True
            return True
        return False

    def _test_attr(self, attr, expected, received):
        exp_attr = getattr(expected, attr, None)
        rec_attr = getattr(received, attr, None)
        if exp_attr is not None and exp_attr != rec_attr:
            self.error = 'Unexpected result for ' \
                         f'{self.name}!\n{attr.title()}: ' \
                         f'{getattr(received, attr, None)}!={getattr(expected, attr, None)}\n' \
                         f'{self.method}'
            self.found_error = True
            return


class ExpectedTest(ValueTest):
    """
    Equal comparison of objects
    """
    def _run_test(self, other_value: TestValueType) -> None:
        op = '__eq__' if self.inverse else '__ne__'
        if getattr(other_value, op)(self.value):
            self.error = f'Unexpected result for {self.name}!\n{other_value}\n'
            self.error += '==' if self.inverse else '!='
            self.error += f'\n{self.value}\n{self.method}'
            self.found_error = True


class ExpectedStatusCodeTest(ValueTest):
    """
    Equal comparison of objects
    """
    def _run_test(self, other_value: Response) -> None:
        op = '__eq__' if self.inverse else '__ne__'
        if getattr(other_value.status_code, op)(self.value):
            self.error = f'Unexpected status_code for {self.name}!\n{other_value.status_code}\n'
            self.error += '==' if self.inverse else '!='
            self.error += f'\n{self.value}\n{self.method}'
            self.found_error = True


class ContainsTest(ValueTest):
    """
    Tests if value member of received value.

    - string/integer: Expected value part of received value (Expected IN Received)
    - dictionary: Expected (key, value)-pairs are within received values
    """
    def _run_test_for_value(self, value_in, other_value: TestValueType) -> bool:
        if isinstance(value_in, (str, int)):
            if self._test_value(value_in, other_value):
                return True
        elif isinstance(value_in, dict):
            if self._test_dict(value_in, other_value):
                return True
        elif isinstance(value_in, list):
            if self._test_list(value_in, other_value):
                return True
        else:
            raise NotImplementedError()
        return False

    def _run_test(self, other_value: TestValueType) -> None:
        self._run_test_for_value(self.value, other_value)

    def _test_response_list(self, value_in, other_value) -> bool:
        errors = []
        for elem in other_value:
            self.found_error = self._test_dict(value_in, elem)
            if self.found_error:
                errors.append(self.error)
                self.found_error = False
                self.error = None
        self.error = errors
        self.found_error = len(self.error) > 0
        return self.found_error

    def _test_list(self, value_in, other_value) -> bool:
        val = False
        errors = []
        for value in value_in:
            new_val = self._run_test_for_value(value, other_value)
            val |= new_val
            if new_val:
                self.found_error = True
                error = f'Unexpected for {self.name}!\n'
                error += f'Didn\'t find key "{value}" in {other_value}'
                errors.append(error)
        self.error = '\n'.join(errors)
        return val

    def _test_dict(self, value_in, other_value) -> bool:
        if isinstance(other_value, list):
            return self._test_response_list(value_in, other_value)

        for key, value in value_in.items():
            if isinstance(value, dict):
                if key in other_value:
                    return self._test_dict(value, other_value[key])
                else:
                    self.found_error = not self.inverse
                    self.error = f'Unexpected for {self.name}!\n'
                    self.error += f'Didn\'t find key "{key}" in {other_value}\n{self.value}\n{self.method}'
                    return self.found_error
            else:
                if key in other_value and isinstance(other_value, dict):
                    if isinstance(other_value[key], list):
                        if self._test_key_in_value(value, other_value[key]):
                            return True
                    elif self._test_exact_value(value, other_value[key]):
                        return True
                elif not self.inverse:
                    return self._test_key_in_value(key, other_value)

        return False

    def _test_value(self, value, other_value) -> bool:
        return self._test_key_in_value(value, other_value)


class ContainsCookiesTest(ValueTest):
    def _get_max_age(self, cookie: Cookie) -> Union[str, datetime.datetime]:
        if cookie.max_age.lower() == 'session':
            return 'session'
        try:
            max_age = datetime.datetime.strptime(cookie.max_age, '%Y-%m-%dT%H:%M:%S%z').timestamp()
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

    def _run_test(self, other_value: TestValueType) -> None:
        if self.inverse:
            raise NotImplementedError()
        else:
            self._run_positive_test(other_value)

    def _test_cookie_age(self, cookie, response_cookie):
        max_age = self._get_max_age(cookie)
        if max_age == 'session':
            if response_cookie.expires is None:
                return True
            self.error = f'Unexpected result for {self.name}!\n' \
                         f'Received for cookie "{cookie.key}" expiration of ' \
                         f'"{response_cookie.expires}", expected "session"'
            self.found_error = True
            return False
        elif response_cookie.expires is None:
            self.error = f'Unexpected result for {self.name}!\n' \
                         f'Received for cookie "{cookie.key}" expiration of ' \
                         f'"session", expected "{cookie.max_age}"'
            self.found_error = True
            return False
        elif abs(max_age.timestamp() - response_cookie.expires) >= 30:
            self.error = 'Unexpected result for ' \
                         f'{self.name}!\n{response_cookie.expires}!={max_age}\n{self.method}'
            self.found_error = True
            return False
        return True

    def _run_positive_test(self, other_value: RequestsCookieJar) -> None:
        not_found = []
        for cookie in self.value:
            found = False
            for response_cookie in other_value:
                if response_cookie.name != cookie.key:
                    continue
                found = True
                attrs = ['domain', 'value']
                for attr in attrs:
                    self._test_attr(attr, cookie, response_cookie)
                if cookie.max_age is not None:
                    if self._test_cookie_age(cookie, response_cookie):
                        continue
            if not found:
                not_found.append(cookie.key)

        if not_found:
            self.error = f'Did not find cookies {", ".join(not_found)}'
            self.found_error = True
            return

from enum import Enum
from typing import List, Union, Dict, Optional

from pydantic import BaseModel, Field, validator


PayloadType = Union[str, Dict, int]


class ConfigType(str, Enum):
    API_TEST = 'api-test'


class AuthHeader(BaseModel):
    Authorization: str = Field(
        ..., description='"Authorization" Header value'
    )


class AuthHeaderTemplate(BaseModel):
    token_position: Optional[str] = Field(
        None,
        description='Position of the authentication token within the response '
                    'object "res", after requesting the desired endpoint'
    )
    auth_header: AuthHeader = Field(..., description='HTTP request header configuration')


class Cookie(BaseModel):
    domain: str = Field(..., description='The domain the cookie is assigned to.')
    key: str = Field(..., description='Name key of the cookie')
    value: Optional[str] = Field(None, description='Value of the cookie')
    path: Optional[str] = Field(None, description='Path assigned to the cookie')
    max_age: Optional[str] = Field(None, description='Expiration time of cookie, can be datetime string or "Session"')


class TestConfig(BaseModel):
    name: str = Field(..., description='A verbose name for the test')
    method: str = Field('get', description='Method to use when calling endpoint')
    endpoint: Optional[str] = Field(None, description='Target endpoint to request from')

    steps: List['TestConfig'] = Field([], description='List of steps, used when multi_step=True')

    uses: Optional[Dict] = Field(None, description='Uses variable in payload/endpoint from previous test')

    # input
    payload: Optional[PayloadType] = Field(None, description='Payload used, can be Dict or Dict/JSON-string')
    payload_cookies: Optional[List[Cookie]] = Field([], description='Cookies send with the request')

    # output tests
    expects_status_code: Optional[int] = Field(None, description='The expected response status code')
    expected: Optional[PayloadType] = Field(
        None, description='Exact comparison values, can be Dict or Dict/JSON-string'
    )
    contains: Optional[PayloadType] = Field(None, description='IN comparison values, can be Dict or Dict/JSON-string')
    contains_not: Optional[PayloadType] = Field(
        None, description='NOT IN comparison values, can be Dict or Dict/JSON-string'
    )
    response_cookies: Optional[List[Cookie]] = Field([], description='Cookies expected with the response')

    auth_header_template: Optional[AuthHeaderTemplate] = Field(
        None, description='Template configuration for header used to perform authenticated requests'
    )

    requires_auth: bool = Field(True, description='Determines if the test uses authentication')
    is_authentication: bool = Field(
        False, description='Determines if this configuration is used to perform an authentication request'
    )
    multi_step: bool = Field(False, description='Determines if test consists of single or multiple steps.')

    @classmethod
    def from_dict(cls, cfg: Dict) -> 'TestConfig':
        auth_header_template = cfg.pop('auth_header_template', None)
        payload = cfg.pop('payload', None)
        contains = cfg.pop('contains', None)
        expected = cfg.pop('expected', None)
        steps = cfg.pop('steps', [])
        return cls(
            **cfg,
            auth_header_template=AuthHeaderTemplate(**auth_header_template) if auth_header_template else None,
            payload=payload,
            expected=expected,
            contains=contains,
            steps=[TestConfig.from_dict(step) for step in steps]
        )

    @validator('is_authentication', 'multi_step')
    @classmethod
    def root_validate(cls, field_value, values, field, config):
        if field_value:
            if field.name == 'is_authentication':
                if 'payload' not in values or values['payload'] is None:
                    raise ValueError('Requires payload.')
                if 'auth_header_template' in values and (val := values['auth_header_template']) is not None:
                    if val.token_position is None or val.auth_header is None:
                        raise ValueError('Requires auth_header_template\'s auth_header and token_position set.')
                else:
                    raise ValueError('Requires auth_header_template.')
            elif field.name == 'multi_step' and 'steps' not in values or len(values['steps']) == 0:
                raise ValueError('Requires steps.')
        return field_value


class ClientConfig(BaseModel):
    base_url: str = Field(..., description='Base URL for the client')
    auth_header: Optional[AuthHeaderTemplate] = Field(
        None, description='Header configuration for authentication when performing requests.'
    )

    @classmethod
    def from_dict(cls, cfg: Dict) -> 'ClientConfig':
        header = cfg.pop('auth_header', None)
        if header is not None:
            header = AuthHeaderTemplate(auth_header=header)
        return cls(
            **cfg,
            auth_header=header
        )


class TestFileConfig(BaseModel):
    client: ClientConfig = Field(..., description='Configuration of the client used in each test.')

    @classmethod
    def from_dict(cls, cfg: Dict) -> 'TestFileConfig':
        return cls(
            client=ClientConfig.from_dict(cfg.get('client', {})) if cfg else None
        )

    @validator('client', pre=True)
    def root_validate(cls, values):
        if values is None:
            raise ValueError('Client undefined.')
        return values


class TestCaseConfig(BaseModel):
    type: ConfigType = Field(..., description='Test case type')
    config: TestFileConfig = Field(
        ..., description='General configuration applied to all included tests in this config.'
    )
    tests: List[TestConfig] = Field(..., description='Test configurations to execute.')

    @classmethod
    def from_dict(cls, cfg: Dict) -> 'TestCaseConfig':
        return cls(
            type=cfg.get('type'),
            config=TestFileConfig.from_dict(cfg.get('config')),
            tests=[TestConfig.from_dict({'name': name, **elem}) for name, elem in cfg.get('tests', {}).items()]
        )

    @validator('type')
    def type_must_be_valid(cls, v):
        return ConfigType(v)


if __name__ == '__main__':
    from .file_loader import TestFileLoader

    c = TestFileLoader._load_content('../smoke_tests/sample.yaml')
    t = TestCaseConfig.from_dict(c)

    print(t)

import os
from enum import Enum
from typing import List, Union, Dict, Optional

from pydantic import BaseModel, Field, validator


PayloadType = Union[str, Dict, int, List, bytes]


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
    headers: Optional[Dict] = Field(None, description='Request headers to send.')

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
    response_headers: Optional[Dict] = Field(None, description='Expected response headers to receive.')

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
        steps = cfg.pop('steps', [])
        return cls(
            **cfg,
            auth_header_template=AuthHeaderTemplate(**auth_header_template) if auth_header_template else None,
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
    kwargs: Optional[Dict] = Field({}, description='Default request kwargs for all tests.')

    @classmethod
    def from_dict(cls, cfg: Dict) -> 'ClientConfig':
        header = cfg.pop('auth_header', None)
        if header is not None:
            header = AuthHeaderTemplate(auth_header=header)
        return cls(
            **cfg,
            auth_header=header
        )


class EnvVar(BaseModel):
    internal_key: str = Field(..., description='internal key')
    external_key: str = Field(..., description='external key')

    @validator('external_key')
    @classmethod
    def root_validate(cls, field_value, values, field, config):
        if field_value is None or field_value not in os.environ:
            raise ValueError(f'Env var "{field_value}" undefined.')
        return field_value


class TestFileConfig(BaseModel):
    client: ClientConfig = Field(..., description='Configuration of the client used in each test.')
    env: Optional[List[EnvVar]] = Field(None, description='List of environment variables to use.')

    @classmethod
    def from_dict(cls, cfg: Dict) -> 'TestFileConfig':
        if cfg is None:
            return cls()

        return cls(
            client=ClientConfig.from_dict(cfg.get('client', {})) if cfg else None,
            env=[EnvVar(internal_key=key, external_key=value) for key, value in cfg.get('env', {}).items()]
            if isinstance(cfg.get('env'), dict) else cfg.get('env')
            if 'env' in cfg else []
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
            if isinstance(cfg.get('tests'), dict) else cfg.get('tests')
        )

    @validator('type')
    def type_must_be_valid(cls, v):
        return ConfigType(v)


class Request(BaseModel):
    Payload: PayloadType = Field(...)
    Protocol: str = Field(...)
    Path: str = Field(...)
    Method: str = Field(...)
    Headers: Dict = Field(...)


class Response(BaseModel):
    Status_code: int = Field(200)
    Body: PayloadType = Field(...)
    Headers: Dict = Field(...)


if __name__ == '__main__':
    from .file_loader import TestFileLoader

    c = TestFileLoader._load_content('../smoke_tests/sample.yaml')
    t = TestCaseConfig.from_dict(c)

    print(t)

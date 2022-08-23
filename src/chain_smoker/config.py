from enum import Enum
from typing import List, Union, Dict, Optional

from pydantic import BaseModel, Field


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


class TestConfig(BaseModel):
    name: str = Field(..., description='A verbose name for the test')
    method: str = Field('get', description='Method to use when calling endpoint')
    endpoint: Optional[str] = Field(None, description='Target endpoint to request from')

    requires_auth: bool = Field(True, description='Determines if the test uses authentication')

    is_authentication: bool = Field(
        False, description='Determines if this configuration is used to perform an authentication request'
    )
    auth_header_template: Optional[AuthHeaderTemplate] = Field(
        None, description='Template configuration for header used to perform authenticated requests'
    )

    multi_step: bool = Field(False, description='Determines if test consists of single or multiple steps.')
    steps: List['TestConfig'] = Field([], description='List of steps, used when multi_step=True')

    uses: Optional[Dict] = Field(None, description='Uses variable in payload/endpoint from previous test')

    # input
    payload: Optional[PayloadType] = Field(None, description='Payload used, can be Dict or Dict/JSON-string')

    # output tests
    expects_status_code: Optional[int] = Field(None, description='The expected response status code')
    expected: Optional[PayloadType] = Field(
        None, description='Exact comparison values, can be Dict or Dict/JSON-string'
    )
    contains: Optional[PayloadType] = Field(None, description='IN comparison values, can be Dict or Dict/JSON-string')
    contains_not: Optional[PayloadType] = Field(None, description='NOT IN comparison values, can be Dict or Dict/JSON-string')

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


class ClientConfig(BaseModel):
    base_url: str = Field('', description='Base URL for the client')
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
            client=ClientConfig.from_dict(cfg.get('client'))
        )


class TestCaseConfig(BaseModel):
    type: ConfigType = Field(..., description='Test case type')
    config: TestFileConfig = Field(
        ..., description='General configuration applied to all included tests in this config.'
    )
    tests: List[TestConfig] = Field(..., description='Test configurations to execute.')

    @classmethod
    def from_dict(cls, cfg: Dict) -> 'TestCaseConfig':
        config = TestFileConfig.from_dict(cfg.get('config'))
        return cls(
            type=ConfigType(cfg.get('type')),
            config=config,
            tests=[TestConfig.from_dict({'name': name, **elem}) for name, elem in cfg.get('tests').items()]
        )


if __name__ == '__main__':
    from .file_loader import TestFileLoader

    c = TestFileLoader._load_content('../smoke_tests/sample.yaml')
    t = TestCaseConfig.from_dict(c)

    print(t)

from typing import List, Union, Dict, Optional

from pydantic import BaseModel, Field


PayloadType = Union[str, Dict, int]


class AuthHeaderTemplate(BaseModel):
    token_position: Optional[str] = Field(None, description='')
    auth_header: Dict


class TestConfig(BaseModel):
    name: str  # required
    multi_step: bool = False
    is_authentication: bool = False
    method: str = 'get'
    endpoint: Optional[str]
    auth_header_template: Optional[AuthHeaderTemplate] = None
    payload: Optional[PayloadType] = None
    expected: Optional[PayloadType] = None
    contains: Optional[PayloadType] = None
    steps: List['TestConfig'] = []

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
    base_url: str = ''
    auth_header: Optional[AuthHeaderTemplate]

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
    client: ClientConfig

    @classmethod
    def from_dict(cls, cfg: Dict) -> 'TestFileConfig':
        return cls(
            client=ClientConfig.from_dict(cfg.get('client'))
        )


class TestCaseConfig(BaseModel):
    type: str  # required
    config: TestFileConfig  # required
    tests: List[TestConfig]  # required

    @classmethod
    def from_dict(cls, cfg: Dict) -> 'TestCaseConfig':
        config = TestFileConfig.from_dict(cfg.get('config'))
        return cls(
            type=cfg.get('type'),
            config=config,
            tests=[TestConfig.from_dict({'name': name, **elem}) for name, elem in cfg.get('tests').items()]
        )


if __name__ == '__main__':
    from main import TestFileLoader

    c = TestFileLoader._load_content('../smoke_tests/sample.yaml')
    t = TestCaseConfig.from_dict(c)

    print(t)

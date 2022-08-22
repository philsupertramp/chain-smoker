from unittest import TestCase

from parameterized import parameterized

from src.chain_smoker.mixins import ExpectedMixin


class ExpectedMixinTestCase(TestCase):
    @parameterized.expand([
        ('{"foo": "bar"}', {"foo": "bar"}),
        ('{"foo": true}', {"foo": True}),
        ("{'foo': True}", {"foo": True}),
        ({"foo": True}, {"foo": True}),
        (None, None),
    ])
    def test_build_expected(self, input_value, expected_value):
        cls = ExpectedMixin()

        self.assertEqual(cls.build_expected(input_value), expected_value)

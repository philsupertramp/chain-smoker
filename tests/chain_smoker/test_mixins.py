from unittest import TestCase

from parameterized import parameterized

from src.chain_smoker.mixins import EvaluationMixin


class EvaluationMixinTestCase(TestCase):
    @parameterized.expand([
        ('{"foo": "bar"}', {'foo': 'bar'}),
        ('{"foo": true}', {'foo': True}),
        ("{'foo': True}", {'foo': True}),
        ({'foo': True}, {'foo': True}),
        (None, None),
    ])
    def test_build_expected(self, input_value, expected_value):
        cls = EvaluationMixin()

        self.assertEqual(cls.evaluate_value(input_value), expected_value)

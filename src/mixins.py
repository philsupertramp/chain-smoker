import ast
import json


class ExpectedMixin:
    @staticmethod
    def build_expected(expected_value):
        expected = None
        if expected_value:
            try:
                expected = ast.literal_eval(expected_value)
            except ValueError:
                expected = json.loads(expected_value)
        return expected

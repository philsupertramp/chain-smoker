import ast
import json


class EvaluationMixin:
    @staticmethod
    def evaluate_value(expected_value):
        expected = None
        if isinstance(expected_value, (list, dict)):
            return expected_value
        if expected_value:
            try:
                expected = ast.literal_eval(expected_value)
            except ValueError:
                expected = json.loads(expected_value)
        return expected

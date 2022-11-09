import sys
import ast
import json


if __name__ == "__main__":
    for line in sys.stdin:
        val = ast.literal_eval(line)
        print(json.dumps(val))

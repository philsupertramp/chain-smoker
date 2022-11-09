import sys
import json


if __name__ == "__main__":
    for line in sys.stdin:
        print(json.dumps(json.loads(line)))

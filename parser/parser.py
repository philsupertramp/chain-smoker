import argparse
import os
import sys
import json
import uuid

from src.parser.file_writer import TestFileWriter

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--directory', type=str, default='smoke_tests/',
                        help='directory to write to')
    parser.add_argument('-f', '--file_name', type=str, default='example',
                        help='file prefix to write to')
    args = parser.parse_args()

    for line in sys.stdin:
        obj = json.loads(line)
        writer = TestFileWriter(obj, os.path.join(args.directory, f'{args.file_name}-{str(uuid.uuid4())[:16]}.yaml'))
        writer.write()

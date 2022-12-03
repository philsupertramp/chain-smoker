#!/usr/bin/env python

import argparse
import os

from src.chain_smoker.file_loader import TestFileLoader


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--directory', type=str, default='smoke_tests/',
                        help='directory to read from')
    args = parser.parse_args()

    filtered_files = filter(lambda f: '.yaml' in f or '.yml' in f, os.listdir(args.directory))
    files = map(lambda x: os.path.join(args.directory, x), filtered_files)
    for file in files:
        loader = TestFileLoader(file)

        loader.run()

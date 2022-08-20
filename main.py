import os

from src.file_loader import TestFileLoader

if __name__ == '__main__':
    files = map(lambda x: os.path.join("smoke_tests/", x), filter(lambda f: '.yaml' in f, os.listdir('smoke_tests')))
    for file in files:
        loader = TestFileLoader(file)

        loader.run()

#!/bin/sh -l

cd /usr/app

python -m chain-smoker.chain-smoker -d /github/workspace/$1

#!/usr/bin/env bash

set -e

HOSTNAME=$1
HOSTNAME=${HOSTNAME:-https://postman-echo.com}
RUN_PARSER=${RUN_PARSER:-true}
OUTPUT_DIR=$2
OUTPUT_DIR=${OUTPUT_DIR:-parsed_examples}
OUTPUT_PREFIX=$3
OUTPUT_PREFIX=${OUTPUT_PREFIX:-example}

# trap ctrl-c and call ctrl_c()
trap ctrl_c INT

function ctrl_c() {
  kill "${PROXY_PID}"
  rm "${settings_file}"
  exit 0
}

function ensure_pipe() {
  pipe=$1
  if [ ! -p "${pipe}" ]
  then
    mkfifo "${pipe}"
  fi
}

ensure_pipe parser_buffer

if [ ! -f "./parser/proxy/build/proxy" ]
then
  mkdir -p "./parser/proxy/build"
  wget "https://github.com/philsupertramp/chain-smoker/releases/download/parser/proxy--linux-amd64.tar.gz" -q -P "./parser/proxy/build"
  tar -xzf "./parser/proxy/build/proxy--linux-amd64.tar.gz" -C "./parser/proxy/build/"
  rm -rf "./parser/proxy/build/proxy--linux-amd64.tar.gz"
  chmod +x "./parser/proxy/build/proxy"
fi

./parser/proxy/build/proxy --host="${HOSTNAME}" > parser_buffer &

PROXY_PID=$!

settings_file=$(mktemp)
echo "on" > "${settings_file}"
echo "Write to ${settings_file} to turn off the parser."

IFS=$'\n'
while read -r line ; do
  if [[ "$(cat "${settings_file}")" == "on" ]]
  then
    (
      echo "${line}" | .venv/bin/python -m parser.parser -d "${OUTPUT_DIR}" -f "${OUTPUT_PREFIX}"
    )
  fi
done < parser_buffer

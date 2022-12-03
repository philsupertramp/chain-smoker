#!/usr/bin/env bash

set -e

# trap ctrl-c and call ctrl_c()
trap ctrl_c INT

function ctrl_c() {
  kill "${PROXY_PID}"
  exit 0
}

function ensure_pipe() {
  pipe=$1
  if [ -p "${pipe}" ]
  then
    rm "${pipe}"
  fi
  mkfifo "${pipe}"
}


HOSTNAME="https://postman-echo.com"
PORT=8080
OUTPUT_DIR=parsed_examples
OUTPUT_PREFIX=example

while getopts h:p:o:f: flag
do
    case "${flag}" in
        h) HOSTNAME=${OPTARG};;
        p) PORT=${OPTARG};;
        o) OUTPUT_DIR=${OPTARG};;
        f) OUTPUT_PREFIX=${OPTARG};;
        a*) ;;
    esac
done

ensure_pipe parser_buffer

./parser/proxy/build/proxy --host="${HOSTNAME}" --port="${PORT}" > parser_buffer &

PROXY_PID=$!

mkdir -p conf
if [ ! -f "conf/parse-conf.yaml" ]
then
  touch "conf/parse-conf.yaml"
fi
settings_file="conf/parse-conf.yaml"

echo "Write to ${settings_file} to turn off the parser."

IFS=$'\n'
while read -r line ; do
  if [[ "$(cat "${settings_file}")" == *"active: true"* ]]
  then
    (
      echo "${line}" | python -m parser.parser -d "${OUTPUT_DIR}" -f "${OUTPUT_PREFIX}"
    )
  fi
done < parser_buffer

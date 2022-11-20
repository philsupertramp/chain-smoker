# Usage
# build-all			: build all containers
# build-parser		: build container for parser
# build-chain-smoker: build container for chain-smoker test runner

build-all : build-parser build-chain-smoker

.PHONY: build-chain-smoker build-parser build-all clean

build-parser:
	docker build . -t chain-smoker-parser -f parser/Dockerfile

build-chain-smoker:
	docker build . -t chain-smoker -f chain-smoker/Dockerfile


clean:
	docker rmi -f chain-smoker-parser chain-smoker

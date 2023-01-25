FROM python:3.10-slim

RUN apt update -y && apt upgrade -y
RUN apt install -y bash wget

RUN useradd -m app-user -s /bin/sh
ENV PATH=$PATH:/home/app-user

WORKDIR /usr/app

RUN pip install -U pip
COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

RUN mkdir -p "/usr/app/parser/proxy/build" && \
  wget "https://github.com/philsupertramp/chain-smoker/releases/download/proxy/proxy-2023-01-25-proxy-linux-amd64.tar.gz" -q -P "/usr/app/parser/proxy/build" && \
  tar -xzf "/usr/app/parser/proxy/build/proxy-2023-01-25-proxy-linux-amd64.tar.gz" -C "/usr/app/parser/proxy/build/" && \
  rm -rf "/usr/app/parser/proxy/build/proxy-2023-01-25-proxy-linux-amd64.tar.gz" && \
  mv "/usr/app/parser/proxy/build/proxy-2023-01-25" "/usr/app/parser/proxy/build/proxy"
  chmod +x "/usr/app/parser/proxy/build/proxy"


COPY ./parser /usr/app/parser
COPY ./src /usr/app/src
RUN chown -R app-user /usr/app

USER app-user

ENTRYPOINT ["/usr/app/parser/run.sh"]

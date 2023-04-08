FROM python:3.10-slim

WORKDIR /usr/app

RUN useradd -m app-user -s /bin/sh
ENV PATH=$PATH:/home/app-user

RUN pip install -U pip

COPY requirements.txt .

RUN pip install -r requirements.txt

COPY src /usr/app/src
COPY chain-smoker /usr/app/chain-smoker
RUN chown -R app-user /usr/app

USER app-user

CMD [ "python", "-m", "chain-smoker.chain-smoker" ]

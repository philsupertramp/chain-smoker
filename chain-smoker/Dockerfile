FROM python:3.10-slim

WORKDIR /usr/app

RUN useradd -m app-user -s /bin/sh
ENV PATH=$PATH:/home/app-user

# Download the latest installer
ADD https://astral.sh/uv/install.sh /uv-installer.sh

# Run the installer then remove it
RUN sh /uv-installer.sh && rm /uv-installer.sh

# Ensure the installed binary is on the `PATH`
ENV PATH="/root/.local/bin/:$PATH"

COPY uv.lock uv.lock
COPY pyproject.toml pyproject.toml

RUN uv sync --locked

COPY src /usr/app/src
COPY chain-smoker /usr/app/chain-smoker
RUN chown -R app-user /usr/app

USER app-user

CMD [ "python", "-m", "chain-smoker.chain-smoker" ]

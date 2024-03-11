FROM python:3.12-bullseye as builder

WORKDIR /app

RUN pip install poetry==1.8.2

COPY pyproject.toml poetry.lock ./
RUN touch README.md

ENV POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=1 \
    POETRY_VIRTUALENVS_CREATE=1 \
    POETRY_CACHE_DIR=/tmp/poetry_cache

RUN --mount=type=cache,target=$POETRY_CACHE_DIR poetry install --without dev --no-root

FROM python:3.12-slim-bullseye as runtime

ENV VIRTUAL_ENV=/app/.venv \
    PATH="/app/.venv/bin:$PATH"

COPY --from=builder ${VIRTUAL_ENV} ${VIRTUAL_ENV}

COPY src/chat_buddy ./chat_buddy

ENTRYPOINT ["python", "-m", "chat_buddy.main"]
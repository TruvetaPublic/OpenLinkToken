##################################################
# Stage 1: Install the Python CLI and its dependencies
##################################################
ARG PYTHON_VERSION=3.11

FROM python:${PYTHON_VERSION}-slim AS build

ENV PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY README.md /app/README.md
COPY lib/python/openlinktoken /app/lib/python/openlinktoken
COPY lib/python/openlinktoken-cli /app/lib/python/openlinktoken-cli

RUN python -m pip install --upgrade pip && \
    python -m pip install --prefix=/install \
        /app/lib/python/openlinktoken \
        /app/lib/python/openlinktoken-cli

##################################################
# Stage 2: Create the image to run the Python CLI
##################################################
FROM python:${PYTHON_VERSION}-slim AS final

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN mkdir /app && \
    addgroup --system appuser && adduser --system --no-create-home --ingroup appuser appuser

COPY --from=build /install /usr/local

WORKDIR /app

RUN chown -R appuser:appuser /app
USER appuser

ENTRYPOINT ["olt"]

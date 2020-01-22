# Docker Multi-Stage build to reduce image size.
# Build compile Image to setup venv with required python packages.
FROM python:3.7.6-alpine AS compile-image
RUN apk add --no-cache --virtual .build-deps gcc musl-dev make

# Use Viertual env to mimize size.
ENV PATH="/usr/venv/bin:$PATH"
RUN python -m venv /usr/venv

# install requirements
WORKDIR /usr/src
COPY ./requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN \
    wget https://get.helm.sh/helm-v3.0.2-linux-amd64.tar.gz && \
    tar -zxvf helm-v3.0.2-linux-amd64.tar.gz

###########################################################
# Build  Target Image.
FROM python:3.7.6-alpine AS build-image

# Copy virtualenv and set it up:
COPY --from=compile-image /usr/venv /usr/venv
ENV PATH="/usr/venv/bin:$PATH"

# set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV PYTHONPATH=".:$PYTHONPATH"

# Copy Helm executable.
COPY --from=compile-image /usr/src/linux-amd64/helm /usr/venv/bin

# add app
WORKDIR /usr/src
COPY app /usr/src/app
COPY charts /usr/src/charts

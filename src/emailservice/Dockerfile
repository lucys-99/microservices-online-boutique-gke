# Copyright 2020 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

FROM --platform=$BUILDPLATFORM python:3.12.8-slim AS base

FROM base AS builder

RUN apt-get update && apt-get install -y \
    build-essential \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip setuptools wheel
# Install with binary preference to avoid compilation issues on ARM
RUN pip install --prefer-binary -r requirements.txt

FROM base
ENV PYTHONUNBUFFERED=1
ENV ENABLE_PROFILER=1

# No need for extra packages in slim as it already has essential libraries

WORKDIR /email_server

COPY --from=builder /usr/local/lib/python3.12/ /usr/local/lib/python3.12/
COPY . .

EXPOSE 8080
ENTRYPOINT [ "python", "email_server.py" ]
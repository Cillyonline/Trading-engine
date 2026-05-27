# Issue 1206 Localhost Staging Compose Evidence

Issue: #1206 - Fix staging compose localhost-only port binding
Date: 2026-05-27

## Scope

The committed runtime change is limited to `docker/staging/docker-compose.staging.yml`, changing the staging API port publish binding to `127.0.0.1:18000:8000`.

The test change is limited to the focused staging deployment contract assertion in `tests/test_staging_deployment_validation.py`.

No live-trading, broker-readiness, production-readiness, or public-exposure claim is introduced.

## Compose Config Evidence

Command:

```powershell
docker compose --env-file .env -f docker/staging/docker-compose.staging.yml config
```

Relevant rendered excerpt:

```yaml
ports:
  - mode: ingress
    host_ip: 127.0.0.1
    target: 8000
    published: "18000"
    protocol: tcp
```

## Exact Compose Build Result

Command:

```powershell
docker compose --env-file .env -f docker/staging/docker-compose.staging.yml up -d --build
```

Result:

```text
#1 [internal] load local bake definitions
#1 reading from stdin 509B 0.0s done
#1 DONE 0.0s

#2 [internal] load build definition from Dockerfile
#2 transferring dockerfile: 948B done
#2 DONE 0.0s

#3 [internal] load metadata for docker.io/library/python:3.12.8-slim
#3 DONE 0.6s

#4 [internal] load .dockerignore
#4 transferring context: 2B done
#4 DONE 0.0s

#5 [1/9] FROM docker.io/library/python:3.12.8-slim@sha256:2199a62885a12290dc9c5be3ca0681d367576ab7bf037da120e564723292a2f0
#5 resolve docker.io/library/python:3.12.8-slim@sha256:2199a62885a12290dc9c5be3ca0681d367576ab7bf037da120e564723292a2f0 0.0s done
#5 DONE 0.0s

#6 [internal] load build context
#6 transferring context: 79.34kB 0.1s done
#6 DONE 0.1s

#7 [2/9] WORKDIR /app
#7 CACHED

#8 [3/9] RUN python -m pip install -U pip uv
#8 CACHED

#9 [4/9] COPY pyproject.toml uv.lock README.md ./
#9 CACHED

#10 [5/9] COPY src ./src
#10 CACHED

#11 [6/9] COPY scripts ./scripts
#11 CACHED

#12 [7/9] RUN uv sync --frozen --no-dev
#12 0.592 Using CPython 3.12.8 interpreter at: /usr/local/bin/python3
#12 0.594 Creating virtual environment at: .venv
#12 0.684    Building cilly-trading @ file:///app
#12 5.653   x Failed to download `setuptools==82.0.0`
#12 5.653   |-> Request failed after 3 retries in 5.0s
#12 5.653   |-> Failed to fetch:
#12 5.653   |   `https://files.pythonhosted.org/packages/e1/c6/76dc613121b793286a3f91621d7b75a2b493e0390ddca50f11993eadf192/setuptools-82.0.0-py3-none-any.whl`
#12 5.653   |-> error sending request for url
#12 5.653   |   (https://files.pythonhosted.org/packages/e1/c6/76dc613121b793286a3f91621d7b75a2b493e0390ddca50f11993eadf192/setuptools-82.0.0-py3-none-any.whl)
#12 5.653   |-> client error (Connect)
#12 5.653   `-> invalid peer certificate: UnknownIssuer
#12 5.653   help: `setuptools` (v82.0.0) was included because `cilly-trading` depends on
#12 5.653         `ccxt` (v4.5.40) which depends on `setuptools`
#12 ERROR: process "/bin/sh -c uv sync --frozen --no-dev" did not complete successfully: exit code: 1
------
 > [7/9] RUN uv sync --frozen --no-dev:
5.653   x Failed to download `setuptools==82.0.0`
5.653   |-> Request failed after 3 retries in 5.0s
5.653   |-> Failed to fetch:
5.653   |   `https://files.pythonhosted.org/packages/e1/c6/76dc613121b793286a3f91621d7b75a2b493e0390ddca50f11993eadf192/setuptools-82.0.0-py3-none-any.whl`
5.653   |-> error sending request for url
5.653   |   (https://files.pythonhosted.org/packages/e1/c6/76dc613121b793286a3f91621d7b75a2b493e0390ddca50f11993eadf192/setuptools-82.0.0-py3-none-any.whl)
5.653   |-> client error (Connect)
5.653   `-> invalid peer certificate: UnknownIssuer
5.653   help: `setuptools` (v82.0.0) was included because `cilly-trading` depends on
5.653         `ccxt` (v4.5.40) which depends on `setuptools`
------
Dockerfile:15

--------------------

  13 |     COPY scripts ./scripts

  14 |     

  15 | >>> RUN uv sync --frozen --no-dev

  16 |     RUN mkdir -p /data/db /data/artifacts /data/logs /data/runtime-state /app/runs/phase6

  17 |     

--------------------

failed to solve: process "/bin/sh -c uv sync --frozen --no-dev" did not complete successfully: exit code: 1
```

## Justified Clean-Build Equivalent Path

The exact Compose build is blocked by local certificate interception for PyPI downloads inside Docker. To validate current-source runtime behavior without changing committed runtime files, a clean image was built from the current source using a temporary Dockerfile input that only adds local dependency-download trust workarounds:

- `pip install --trusted-host pypi.org --trusted-host files.pythonhosted.org`
- `UV_INSECURE_HOST="pypi.org files.pythonhosted.org"` for `uv sync`

No committed source, Compose, API, authentication, or runtime behavior was changed for this workaround.

Command:

```powershell
$dockerfile = Get-Content -Raw docker/staging/Dockerfile
$dockerfile = $dockerfile -replace 'RUN python -m pip install -U pip uv', 'RUN python -m pip install --trusted-host pypi.org --trusted-host files.pythonhosted.org -U pip uv'
$replacement = "ENV UV_INSECURE_HOST=`"pypi.org files.pythonhosted.org`"`nRUN uv sync --frozen --no-dev"
$dockerfile = $dockerfile -replace 'RUN uv sync --frozen --no-dev', $replacement
$dockerfile | docker build --no-cache -t staging-api:issue-1206-clean -f - .
docker tag staging-api:issue-1206-clean staging-api:latest
docker compose --env-file .env -f docker/staging/docker-compose.staging.yml up -d --no-build
```

Exact output:

```text
docker : #0 building with "desktop-linux" instance using docker driver
In Zeile:7 Zeichen:15
+ ... ockerfile | docker build --no-cache -t staging-api:issue-1206-clean - ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : NotSpecified: (#0 building wit...g docker driver:String) [], RemoteException
    + FullyQualifiedErrorId : NativeCommandError
 
#1 [internal] load build definition from Dockerfile
#1 transferring dockerfile: 1.07kB 0.0s done
#1 DONE 0.0s
#2 [internal] load metadata for docker.io/library/python:3.12.8-slim
#2 DONE 1.1s
#3 [internal] load .dockerignore
#3 transferring context: 2B done
#3 DONE 0.0s
#4 [1/9] FROM 
docker.io/library/python:3.12.8-slim@sha256:2199a62885a12290dc9c5be3ca0681d367576ab7bf037da120e564723292a2f0
#4 resolve 
docker.io/library/python:3.12.8-slim@sha256:2199a62885a12290dc9c5be3ca0681d367576ab7bf037da120e564723292a2f0 0.0s done
#4 DONE 0.0s
#5 [2/9] WORKDIR /app
#5 CACHED
#6 [internal] load build context
#6 transferring context: 176.29kB 0.1s done
#6 DONE 0.1s
#7 [3/9] RUN python -m pip install --trusted-host pypi.org --trusted-host files.pythonhosted.org -U pip uv
#7 2.183 Requirement already satisfied: pip in /usr/local/lib/python3.12/site-packages (24.3.1)
#7 2.371 Collecting pip
#7 2.505   Downloading pip-26.1.1-py3-none-any.whl.metadata (4.6 kB)
#7 3.113 Collecting uv
#7 3.146   Downloading uv-0.11.16-py3-none-manylinux_2_17_x86_64.manylinux2014_x86_64.whl.metadata (11 kB)
#7 3.189 Downloading pip-26.1.1-py3-none-any.whl (1.8 MB)
#7 3.800    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 1.8/1.8 MB 3.1 MB/s eta 0:00:00
#7 3.839 Downloading uv-0.11.16-py3-none-manylinux_2_17_x86_64.manylinux2014_x86_64.whl (24.7 MB)
#7 5.622    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 24.7/24.7 MB 14.2 MB/s eta 0:00:00
#7 5.676 Installing collected packages: uv, pip
#7 6.124   Attempting uninstall: pip
#7 6.129     Found existing installation: pip 24.3.1
#7 6.168     Uninstalling pip-24.3.1:
#7 6.438       Successfully uninstalled pip-24.3.1
#7 7.459 Successfully installed pip-26.1.1 uv-0.11.16
#7 7.459 WARNING: Running pip as the 'root' user can result in broken permissions and conflicting behaviour with the 
system package manager, possibly rendering your system unusable.It is recommended to use a virtual environment 
instead: https://pip.pypa.io/warnings/venv. Use the --root-user-action option if you know what you are doing and want 
to suppress this warning.
#7 DONE 7.9s
#8 [4/9] COPY pyproject.toml uv.lock README.md ./
#8 DONE 0.1s
#9 [5/9] COPY src ./src
#9 DONE 0.5s
#10 [6/9] COPY scripts ./scripts
#10 DONE 0.1s
#11 [7/9] RUN uv sync --frozen --no-dev
#11 0.416 Using CPython 3.12.8 interpreter at: /usr/local/bin/python3
#11 0.416 Creating virtual environment at: .venv
#11 0.451    Building cilly-trading @ file:///app
#11 1.188 Downloading pandas (10.4MiB)
#11 1.189 Downloading numpy (15.8MiB)
#11 1.213 Downloading uvloop (4.2MiB)
#11 1.219 Downloading coincurve (1.5MiB)
#11 1.219 Downloading curl-cffi (7.9MiB)
#11 1.220 Downloading sqlalchemy (3.2MiB)
#11 1.221 Downloading ccxt (6.2MiB)
#11 1.227 Downloading pydantic-core (2.0MiB)
#11 1.231 Downloading aiohttp (1.7MiB)
#11 1.233 Downloading cryptography (4.3MiB)
#11 3.447    Building multitasking==0.0.12
#11 5.475  Downloaded coincurve
#11 5.832  Downloaded aiohttp
#11 6.465  Downloaded pydantic-core
#11 7.391  Downloaded sqlalchemy
#11 7.990  Downloaded uvloop
#11 8.195  Downloaded cryptography
#11 9.358       Built multitasking==0.0.12
#11 9.753       Built cilly-trading @ file:///app
#11 10.46  Downloaded ccxt
#11 11.11  Downloaded curl-cffi
#11 12.99  Downloaded pandas
#11 14.26  Downloaded numpy
#11 14.26 Prepared 66 packages in 13.83s
#11 14.37 Installed 66 packages in 113ms
#11 14.37  + aiodns==4.0.0
#11 14.37  + aiohappyeyeballs==2.6.1
#11 14.37  + aiohttp==3.13.3
#11 14.37  + aiosignal==1.4.0
#11 14.37  + aiosqlite==0.22.1
#11 14.37  + annotated-doc==0.0.4
#11 14.37  + annotated-types==0.7.0
#11 14.37  + anyio==4.12.1
#11 14.37  + attrs==25.4.0
#11 14.37  + beautifulsoup4==4.14.3
#11 14.37  + ccxt==4.5.40
#11 14.37  + certifi==2026.2.25
#11 14.37  + cffi==2.0.0
#11 14.37  + charset-normalizer==3.4.4
#11 14.37  + cilly-trading==0.1.0 (from file:///app)
#11 14.37  + click==8.3.1
#11 14.37  + coincurve==21.0.0
#11 14.37  + cryptography==46.0.5
#11 14.37  + curl-cffi==0.13.0
#11 14.37  + deprecated==1.3.1
#11 14.37  + fastapi==0.135.1
#11 14.37  + frozendict==2.4.7
#11 14.37  + frozenlist==1.8.0
#11 14.37  + greenlet==3.3.2
#11 14.37  + h11==0.16.0
#11 14.37  + httpcore==1.0.9
#11 14.37  + httptools==0.7.1
#11 14.37  + httpx==0.28.1
#11 14.37  + idna==3.11
#11 14.37  + limits==5.8.0
#11 14.37  + multidict==6.7.1
#11 14.37  + multitasking==0.0.12
#11 14.37  + numpy==2.4.2
#11 14.37  + packaging==26.0
#11 14.37  + pandas==3.0.1
#11 14.37  + peewee==4.0.1
#11 14.37  + platformdirs==4.9.2
#11 14.37  + prometheus-client==0.25.0
#11 14.37  + propcache==0.4.1
#11 14.37  + protobuf==7.34.0
#11 14.37  + pycares==5.0.1
#11 14.37  + pycparser==3.0
#11 14.37  + pydantic==2.12.5
#11 14.37  + pydantic-core==2.41.5
#11 14.37  + pyjwt==2.12.1
#11 14.37  + python-dateutil==2.9.0.post0
#11 14.37  + python-dotenv==1.2.2
#11 14.37  + pytz==2026.1.post1
#11 14.37  + pyyaml==6.0.3
#11 14.37  + requests==2.32.5
#11 14.37  + setuptools==82.0.0
#11 14.37  + six==1.17.0
#11 14.37  + slowapi==0.1.9
#11 14.37  + soupsieve==2.8.3
#11 14.37  + sqlalchemy==2.0.48
#11 14.37  + starlette==0.52.1
#11 14.37  + typing-extensions==4.15.0
#11 14.37  + typing-inspection==0.4.2
#11 14.37  + urllib3==2.6.3
#11 14.37  + uvicorn==0.41.0
#11 14.37  + uvloop==0.22.1
#11 14.37  + watchfiles==1.1.1
#11 14.37  + websockets==16.0
#11 14.37  + wrapt==2.1.2
#11 14.37  + yarl==1.23.0
#11 14.37  + yfinance==0.2.66
#11 DONE 14.7s
#12 [8/9] RUN mkdir -p /data/db /data/artifacts /data/logs /data/runtime-state /app/runs/phase6
#12 DONE 0.5s
#13 [9/9] WORKDIR /data
#13 DONE 0.1s
#14 exporting to image
#14 exporting layers
#14 exporting layers 13.1s done
#14 exporting manifest sha256:a2b99bdab440df8d4864d7d22faf778afbeb757f5e7721041bf4e04f5451916a 0.0s done
#14 exporting config sha256:d34d117d4d3a87f4d8d055325f9c089d7f2c0672606f8c733c2e13aa759d137a 0.0s done
#14 exporting attestation manifest sha256:575ed4172df817ad125aeaabfe05af0d76b566f2c339840860a2f5237145fe7b 0.1s done
#14 exporting manifest list sha256:12a0af94d2f6285e26500a6741391fc7394b1ec7227a354e55a72c199b4d00ee
#14 exporting manifest list sha256:12a0af94d2f6285e26500a6741391fc7394b1ec7227a354e55a72c199b4d00ee 0.0s done
#14 naming to docker.io/library/staging-api:issue-1206-clean done
#14 unpacking to docker.io/library/staging-api:issue-1206-clean
#14 unpacking to docker.io/library/staging-api:issue-1206-clean 5.7s done
#14 DONE 19.0s
docker :  Network staging_default  Creating
In Zeile:9 Zeichen:1
+ docker compose --env-file .env -f docker/staging/docker-compose.stagi ...
+ ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : NotSpecified: ( Network staging_default  Creating:String) [], RemoteException
    + FullyQualifiedErrorId : NativeCommandError
 
 Network staging_default  Created
 Container staging-api-1  Creating
 Container staging-api-1  Created
 Container staging-api-1  Starting
 Container staging-api-1  Started
```

The `docker tag staging-api:issue-1206-clean staging-api:latest` command emitted no stdout or stderr and completed before the committed Compose command was run.

No stale cached-image acceptance is claimed here: the accepted runtime evidence uses the `staging-api:issue-1206-clean` image built above with `--no-cache` from the current source context, tagged to `staging-api:latest`, then started through the committed Compose file with `up -d --no-build`.

## Runtime Port Evidence

Command:

```powershell
docker compose --env-file .env -f docker/staging/docker-compose.staging.yml ps
```

Output:

```text
NAME            IMAGE         COMMAND                  SERVICE   CREATED          STATUS                    PORTS
staging-api-1   staging-api   "uvicorn api.main:ap..."   api       13 seconds ago   Up 13 seconds (healthy)   127.0.0.1:18000->8000/tcp
```

This output contains neither `0.0.0.0:18000->8000/tcp` nor `[::]:18000->8000/tcp`.

## Health Endpoint Evidence

Commands:

```powershell
curl.exe -sS -H "X-Cilly-Role: read_only" http://127.0.0.1:18000/health
curl.exe -sS -H "X-Cilly-Role: read_only" http://127.0.0.1:18000/health/engine
curl.exe -sS -H "X-Cilly-Role: read_only" http://127.0.0.1:18000/health/data
curl.exe -sS -H "X-Cilly-Role: read_only" http://127.0.0.1:18000/health/guards
```

Output:

```text
/health
{"status":"healthy","ready":true,"mode":"running","reason":"bounded_runtime_ready","runtime_status":"healthy","runtime_reason":"runtime_running_fresh","checked_at":"2026-05-27T14:07:31.640492+00:00"}

/health/engine
{"subsystem":"engine","status":"healthy","ready":true,"mode":"running","reason":"bounded_runtime_ready","runtime_status":"healthy","runtime_reason":"runtime_running_fresh","checked_at":"2026-05-27T14:07:31.679720+00:00"}

/health/data
{"subsystem":"data","status":"healthy","ready":true,"reason":"data_source_available","checked_at":"2026-05-27T14:07:31.714348+00:00","external_data_gate":"disabled"}

/health/guards
{"subsystem":"guards","status":"healthy","ready":true,"decision":"allowing","blocking":false,"guards":{"drawdown_guard":{"enabled":false,"blocking":false},"daily_loss_guard":{"enabled":false,"blocking":false},"kill_switch":{"active":false,"blocking":false}},"checked_at":"2026-05-27T14:07:31.753466+00:00"}
```

## Focused Test Evidence

Command:

```powershell
python -m pytest tests/test_staging_deployment_validation.py tests/test_staging_deployment_docs.py tests/test_staging_env_contract.py
```

Output:

```text
============================= test session starts =============================
platform win32 -- Python 3.13.2, pytest-8.4.1, pluggy-1.6.0
rootdir: C:\repos\Trading-engine
configfile: pytest.ini
plugins: anyio-4.9.0
collected 9 items

tests\test_staging_deployment_validation.py ....                         [ 44%]
tests\test_staging_deployment_docs.py ..                                 [ 66%]
tests\test_staging_env_contract.py ...                                   [100%]

============================= 9 passed in 11.97s ==============================
```

## Full Regression Evidence

Command:

```powershell
$env:UV_INSECURE_HOST='pypi.org files.pythonhosted.org'; python -m uv run -- python -m pytest --import-mode=importlib
```

Output summary:

```text
============================= test session starts =============================
platform win32 -- Python 3.13.2, pytest-9.0.2, pluggy-1.6.0
rootdir: C:\repos\Trading-engine
configfile: pytest.ini
plugins: anyio-4.12.1, cov-7.1.0
collected 1587 items
...
============================== warnings summary ===============================
src/api/test_auth_api.py::TestJwtAuthUnit::test_wrong_algorithm_raises
  C:\repos\Trading-engine\.venv\Lib\site-packages\jwt\api_jwt.py:147: InsecureKeyLengthWarning: The HMAC key is 6 bytes long, which is below the minimum recommended length of 32 bytes for SHA256. See RFC 7518 Section 3.2.
    return self._jws.encode(

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
=========== 1586 passed, 1 skipped, 1 warning in 124.50s (0:02:04) ============
   Building cilly-trading @ file:///C:/repos/Trading-engine
      Built cilly-trading @ file:///C:/repos/Trading-engine
Uninstalled 2 packages in 39ms
Installed 13 packages in 164ms
```

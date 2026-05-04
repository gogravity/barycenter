# ETL container image for the Barycenter nightly CW sync.
# Runs inside a VNet-injected Container Apps Job (caj-bary-etl) so it can reach
# the private endpoints for SQL, Key Vault, and WORM storage.
#
# Auth at runtime: DefaultAzureCredential resolves to the mi-bary-etl
# user-assigned managed identity attached to the Container Apps Job.

FROM python:3.12-slim

# Microsoft ODBC Driver 18 for SQL Server (required by pyodbc).
# https://learn.microsoft.com/sql/connect/odbc/linux-mac/installing-the-microsoft-odbc-driver-for-sql-server
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
        gnupg2 \
        unixodbc-dev \
    && curl -fsSL https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg \
    && curl -fsSL https://packages.microsoft.com/config/debian/12/prod.list \
        > /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y --no-install-recommends msodbcsql18 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install barycenter-audit first (local dependency of barycenter-etl).
COPY packages/barycenter-audit /app/packages/barycenter-audit
RUN pip install --no-cache-dir /app/packages/barycenter-audit

# Install barycenter-etl.
COPY packages/barycenter-etl /app/packages/barycenter-etl
RUN pip install --no-cache-dir /app/packages/barycenter-etl

# CanaryScanner resolves compliance/cui-canary-phrases.yaml relative to CWD (/app).
# The repo-root resolution (parents[6]) is wrong for an installed package, so we
# rely on the CWD fallback instead by shipping the file at /app/compliance/.
COPY compliance /app/compliance

# Non-root user for principle of least privilege.
RUN useradd --system --no-create-home etl
USER etl

ENTRYPOINT ["python", "-m", "barycenter.etl.run", "--adapter", "connectwise"]

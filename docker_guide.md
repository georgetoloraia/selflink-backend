# 🐳 SelfLink Backend — Docker Quick Guide

This guide explains how to **run**, **stop**, **rebuild**, and **manage** every container defined under `infra/compose.yaml` and `infra/Makefile`.

---

## 🚀 Start the Infrastructure

**Modern Docker (Compose V2 plugin):**

```bash
make -C infra up
```

**Legacy binary (`docker-compose`):**

```bash
COMPOSE=docker-compose make -C infra up
```

This will build the API/worker/realtime images, start Postgres, Redis, and Pgbouncer, and launch the Django API + ASGI + Celery worker + realtime gateway.

Optional profiles:

```bash
docker compose -f infra/compose.yaml --profile search up -d
docker compose -f infra/compose.yaml --profile storage up -d
```

Realtime gateway (FastAPI) is enabled by default; no profile is required.

---

## 🧱 Check Containers

List running containers:

```bash
docker ps
```

Check service status via Compose:

```bash
docker compose -f infra/compose.yaml ps
# or: docker-compose -f infra/compose.yaml ps
```

---

## 📜 Logs

Follow logs from all services:

```bash
make -C infra logs
```

Manual alternative:

```bash
docker compose -f infra/compose.yaml logs -f
```

Tail a single service (example: `api`):

```bash
docker compose -f infra/compose.yaml logs -f api
```

---

## 🔁 Rebuild / Restart

Rebuild every container:

```bash
docker compose -f infra/compose.yaml build --no-cache
```

Rebuild + restart one service (example: `api`):

```bash
docker compose -f infra/compose.yaml up -d --build api
```

Restart everything without rebuilding:

```bash
docker compose -f infra/compose.yaml restart
```

---

## 🛑 Stop / Remove Containers

Stop and remove all containers:

```bash
make -C infra down
```

Manual variant (also removes named volumes):

```bash
docker compose -f infra/compose.yaml down -v
```

---

## ⚙️ Environment Notes

Ensure `infra/.env` exists before booting the stack:

```bash
cp infra/.env.example infra/.env
```

Docker Compose reads `infra/.env` (the root `.env` is only for non-Docker runs). Use Docker service hostnames like `pgbouncer`, `redis`, and `opensearch` instead of `localhost` in container URLs. `infra/.env` must define `REALTIME_JWT_SECRET`, database URLs, Redis/OpenSearch hosts, and MinIO credentials. After changing `infra/.env`, rebuild affected services:

```bash
docker compose -f infra/compose.yaml up -d --build
```

---

## 🧩 Dev vs prod server modes

- `infra/compose.yaml` runs Django via `runserver` for local development.
- `infra/docker/Dockerfile.api` defaults to Gunicorn for production-like deployments.

## 🧰 Troubleshooting

- **Permission denied / Docker not running**

  ```bash
  sudo systemctl start docker
  sudo usermod -aG docker $USER
  # log out/in afterward
  ```

- **Missing Compose V2 plugin**

  ```bash
  sudo apt-get update
  sudo apt-get install docker-compose-plugin
  ```

- **`KeyError: 'ContainerConfig'` when running `docker-compose`**

  Docker Engine 25+ removed a legacy field that the standalone `docker-compose` 1.x binary still expects, so `docker-compose up` now crashes with `KeyError: 'ContainerConfig'`. Fix it by switching to the V2 plugin:

  ```bash
  sudo apt-get update
  sudo apt-get install docker-compose-plugin
  make -C infra up  # uses `docker compose` automatically
  ```

  If you must keep using the standalone binary, install the Compose V2 CLI release (not the legacy 1.x build):

  ```bash
  sudo curl -L "https://github.com/docker/compose/releases/download/v2.27.1/docker-compose-linux-x86_64" -o /usr/local/bin/docker-compose
  sudo chmod +x /usr/local/bin/docker-compose
  COMPOSE=docker-compose make -C infra up
  ```

---

## ✅ Common Commands

| Action                      | Command                                                       |
| --------------------------- | ------------------------------------------------------------- |
| Run all services            | `make -C infra up`                                            |
| Stop everything             | `make -C infra down`                                          |
| Rebuild everything          | `docker compose -f infra/compose.yaml build --no-cache`       |
| View logs                   | `make -C infra logs`                                          |
| Rebuild one service (api)   | `docker compose -f infra/compose.yaml up -d --build api`      |
| Remove all + volumes        | `docker compose -f infra/compose.yaml down -v`                |

---

## 🧠 After `make -C infra up`

- Django API → <http://localhost:8000>
- ASGI (SSE) → <http://localhost:8001>
- Realtime Gateway (FastAPI) → `ws://localhost:8002/ws`
- MinIO Console → <http://localhost:9001> (profile `storage`)
- OpenSearch → <http://localhost:9200> (profile `search`)

© 2025 SelfLink Project — Maintainer: @georgetoloraia

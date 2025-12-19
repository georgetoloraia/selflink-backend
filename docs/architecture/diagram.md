# Architecture Diagram

```
                +------------------+
                |  Mobile / Web UI |
                +---------+--------+
                          |
                          v
                +---------+--------+
                |     API (DRF)    |
                +----+--------+----+
                     |        |
                     |        +------------------+
                     |                           |
                     v                           v
          +----------+----------+     +----------+----------+
          |   Core Platform     |     |    Intelligence     |
          | users/social/pay    |     | mentor/astro/match  |
          +----------+----------+     +----------+----------+
                     |                           |
                     +-------------+-------------+
                                   |
                                   v
                           +-------+-------+
                           |   PostgreSQL  |
                           +-------+-------+
                                   |
                                   v
                          +--------+--------+
                          |   Redis / Cache |
                          +-----------------+
```

Notes:
- Core reads from Intelligence only via public interfaces.
- Heavy compute is queued to Celery workers.
- SSE runs through ASGI (uvicorn/daphne).

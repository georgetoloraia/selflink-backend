# selflink-backend

```
selflink-backend/
│
├── apps/
│   ├── users/              # auth, profiles, privacy
│   ├── social/             # posts, comments, likes, follow
│   ├── messaging/          # threads, messages
│   ├── mentor/             # AI mentor core
│   ├── matrix/             # astro/matrix logic
│   ├── payments/           # wallet, subscriptions
│   ├── notifications/      # push/email notifications
│   ├── moderation/         # reports, bans
│   └── feed/               # feed ranking system
│
├── services/
│   ├── realtime/           # FastAPI WebSocket gateway
│   └── reco/               # recommendation workers
│
├── core/
│   ├── settings/
│   │   ├── base.py
│   │   ├── dev.py
│   │   └── prod.py
│   ├── urls.py
│   ├── asgi.py
│   └── wsgi.py
│
├── libs/
│   ├── idgen.py
│   └── utils/
│
├── infra/
│   ├── docker/
│   ├── compose.yaml
│   ├── k8s/
│   └── Makefile
│
├── tests/
│
├── manage.py
├── requirements.txt
└── README.md
```
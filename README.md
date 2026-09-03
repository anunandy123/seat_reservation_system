# Smart Seat Reservation

A Django seat reservation demo with live availability, multi-seat selection, two-minute holds, and transactional booking.

## Run locally

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python manage.py migrate
.venv/bin/python manage.py runserver
```

Open http://127.0.0.1:8000/. The seat map refreshes every five seconds. Each reservation and checkout operation uses `transaction.atomic()` and `select_for_update()` so competing requests cannot claim the same seat.

For production, set `DJANGO_DEBUG=0`, provide a long random `DJANGO_SECRET_KEY`, configure `DJANGO_ALLOWED_HOSTS` and `DATABASE_URL`, and use PostgreSQL. SQLite does not provide real row-level locking for concurrent requests.

The included `docker-compose.yml` starts PostgreSQL for a concurrency-safe local run:

```bash
docker compose up -d db
DATABASE_URL=postgresql://seat:seat@127.0.0.1:5432/seat_reserve .venv/bin/python manage.py migrate
DATABASE_URL=postgresql://seat:seat@127.0.0.1:5432/seat_reserve .venv/bin/python manage.py runserver
```

Run tests with `.venv/bin/python manage.py test`.

## Deploy to Render

1. Push this project to a GitHub or GitLab repository.
2. In Render, choose **New > Blueprint** and select the repository.
3. Render detects `render.yaml`, creates the web service and PostgreSQL database, installs dependencies, collects static files, and runs migrations.
4. Open the generated `onrender.com` URL.

The blueprint uses Gunicorn and WhiteNoise for production serving. Keep the PostgreSQL database attached: the reservation transactions require a database with row-level locking, and Render's local filesystem is not persistent.

To deploy manually instead, create a Render PostgreSQL database and web service with:

```text
Build command: pip install -r requirements.txt && python manage.py collectstatic --no-input && python manage.py migrate
Start command: gunicorn config.wsgi:application
```

Set `DATABASE_URL` from the database's internal connection string, `DJANGO_DEBUG=0`, generate a long `DJANGO_SECRET_KEY`, and set `DJANGO_ALLOWED_HOSTS` to the Render hostname.
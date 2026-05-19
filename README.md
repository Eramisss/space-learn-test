# Веб-приложение для обучения с использованием интервальных повторений

**ВКР:** Зырянов Э.А., группа Б-ИВТ-22-1
**Алгоритм:** SM-2 (SuperMemo 2, Piotr Wozniak, 1987)

## Локальный запуск (для разработки)

```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python manage.py makemigrations accounts decks cards reviews
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

## Тесты

```bash
python manage.py test apps.reviews.tests -v 2
python manage.py test apps.tests_api -v 2
```

## Деплой на облачный сервер (Docker Compose)

Стек: **PostgreSQL 16 + Gunicorn + Nginx** в трёх контейнерах.

### 1. Подготовка сервера

На сервере должны быть установлены `docker` и `docker compose` (Docker Engine 20.10+).

### 2. Конфигурация окружения

```bash
cp .env.example .env
# Сгенерируйте секретный ключ
python -c "from secrets import token_urlsafe; print(token_urlsafe(50))"
# Отредактируйте .env: вставьте SECRET_KEY, задайте ALLOWED_HOSTS (IP/домен сервера),
# CSRF_TRUSTED_ORIGINS (http://<IP-или-домен>), пароль БД
nano .env
```

### 3. Сборка и запуск

```bash
docker compose up -d --build
```

Контейнер `backend` при старте автоматически:
1. Дожидается готовности PostgreSQL
2. Применяет миграции (`makemigrations` + `migrate`)
3. Собирает статику (`collectstatic`)
4. Запускает Gunicorn

### 4. Создание суперпользователя

```bash
docker compose exec backend python manage.py createsuperuser
```

### 5. Проверка

Откройте `http://<IP-сервера>/` — должен открыться SPA. Админка: `/admin/`, API: `/api/`.

### Полезные команды

```bash
docker compose logs -f                 # все логи
docker compose logs -f backend         # только бэкенд
docker compose restart backend         # рестарт после правок кода
docker compose down                    # остановить (БД сохранится в volume)
docker compose down -v                 # снести вместе с БД
docker compose exec db psql -U postgres spaced_repetition   # psql в БД
```

### Архитектура контейнеров

```
[Browser] → :80 [nginx] → /static/, /media/  → static_volume, media_volume
                       → /api/, /admin/      → [backend :8000 gunicorn] → [db :5432 postgres]
                       → / (SPA)             → frontend/index.html
```

### Что дальше (опционально)

- **HTTPS**: добавить `certbot` контейнер + конфиг `listen 443 ssl` в `nginx.conf`
- **Бэкапы БД**: `docker compose exec db pg_dump -U postgres spaced_repetition > backup.sql`

## Структура: см. дерево файлов в проекте

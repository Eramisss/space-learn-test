# Архитектура веб-приложения

Трёхзвенная архитектура: клиент (SPA) — сервер приложений (Django + Nginx) — СУБД (PostgreSQL).
Серверная часть упакована в Docker-контейнеры и оркестрируется Docker Compose.

```mermaid
flowchart TB
    subgraph client["КЛИЕНТ"]
        direction TB
        Browser["Браузер пользователя"]
        SPA["React 18 SPA (UMD + Babel-standalone)<br/>frontend/index.html<br/>JWT в localStorage"]
        Browser -.->|"загружает HTML/JS/CSS"| SPA
    end

    subgraph server["ОБЛАЧНЫЙ СЕРВЕР  ·  Ubuntu 24.04  ·  Docker Compose"]
        direction TB

        subgraph nginx_box["Контейнер nginx:1.27-alpine"]
            Nginx["<b>Nginx</b><br/>порт 80<br/>reverse proxy<br/>раздача статики и SPA"]
        end

        subgraph backend_box["Контейнер backend (Python 3.12-slim)"]
            direction TB
            Gunicorn["<b>Gunicorn</b><br/>WSGI · 3 worker'а · :8000"]
            DRF["<b>Django 5 + DRF 3.15</b><br/>Simple JWT (access 1ч / refresh 7д)"]
            subgraph apps["Приложения"]
                direction LR
                Accounts["accounts<br/>(регистрация, JWT)"]
                Decks["decks"]
                Cards["cards"]
                Reviews["<b>reviews</b><br/><i>алгоритм SM-2</i>"]
                Stats["stats<br/>(аналитика)"]
            end
            Gunicorn --> DRF --> apps
        end

        subgraph db_box["Контейнер postgres:16-alpine"]
            DB[("<b>PostgreSQL 16</b><br/>5 таблиц<br/>auth_user, profile,<br/>deck, card, reviewlog")]
        end

        subgraph volumes["Постоянные тома (volumes)"]
            direction LR
            PgVol[("postgres_data")]
            StaticVol[("static_volume")]
            MediaVol[("media_volume")]
        end
    end

    Browser ==>|"HTTP :80"| Nginx
    Nginx -->|"/ → frontend/index.html"| Browser
    Nginx -->|"/static/, /media/"| Browser
    Nginx ==>|"/api/*, /admin/*<br/>proxy_pass :8000"| Gunicorn
    apps ==>|"psycopg 3<br/>(driver)"| DB
    DB -.- PgVol
    apps -.->|"collectstatic"| StaticVol
    Nginx -.- StaticVol
    Nginx -.- MediaVol

    classDef container fill:#E8F4FD,stroke:#2563EB,stroke-width:2px
    classDef store fill:#FEF3C7,stroke:#D97706,stroke-width:2px
    classDef client_cls fill:#F3E8FF,stroke:#7C3AED,stroke-width:2px
    class nginx_box,backend_box,db_box container
    class DB,PgVol,StaticVol,MediaVol store
    class Browser,SPA client_cls
```

## Поток типового запроса

**Загрузка приложения** (вход на сайт):
1. Браузер → `GET http://147.45.143.248/` → **Nginx**
2. Nginx отдаёт `frontend/index.html` (смонтирован как `:ro` volume)
3. Браузер качает React, ReactDOM, Babel с CDN и исполняет SPA

**API-запрос** (например, повторение карточки):
1. Браузер → `POST /api/review/answer/` с `Authorization: Bearer <JWT>` → **Nginx**
2. Nginx по правилу `location ~ ^/(api|admin)/` проксирует в `http://backend:8000`
3. **Gunicorn** передаёт запрос Django; **Simple JWT** валидирует токен
4. View вызывает `SM2Engine.process_review()` → пересчитывает `EF`, интервал, дату следующего показа
5. Запись `ReviewLog` сохраняется в **PostgreSQL** через psycopg
6. JSON-ответ возвращается обратно той же цепочкой

## Соответствие компонентов файлам проекта

| Компонент схемы          | В репозитории                                    |
|--------------------------|--------------------------------------------------|
| React SPA                | `frontend/index.html`, `frontend/App.jsx`        |
| Nginx-конфиг             | `nginx/nginx.conf`                               |
| Backend-образ            | `backend/Dockerfile`, `backend/entrypoint.sh`    |
| Django-настройки         | `backend/config/settings.py`                     |
| Маршрутизация API        | `backend/config/urls.py`, `backend/apps/*/urls.py` |
| Алгоритм SM-2            | `backend/apps/reviews/models.py` (`SM2Engine`)   |
| Оркестрация контейнеров  | `docker-compose.yml`                             |
| Переменные окружения     | `.env` (из шаблона `.env.example`)               |

## Используемые технологии

| Слой       | Технологии                                                    |
|------------|---------------------------------------------------------------|
| Frontend   | React 18, JavaScript (JSX через Babel-standalone), CSS-vars   |
| Backend    | Python 3.12, Django 5.0.6, Django REST Framework 3.15, Simple JWT 5.3, Gunicorn 22, psycopg 3 |
| СУБД       | PostgreSQL 16                                                 |
| Reverse proxy | Nginx 1.27                                                 |
| Инфраструктура | Docker Engine, Docker Compose, Ubuntu Server 24.04 LTS    |

## Как получить картинку для Word/ВКР

1. https://mermaid.live → вставить содержимое блока ```mermaid из этого файла
2. **Actions → Download PNG** (поднять масштаб через шестерёнку, иначе шрифт мелкий)
3. Вставить в Word

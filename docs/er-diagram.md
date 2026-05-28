# ER-диаграмма базы данных

Схема построена по моделям Django (`backend/apps/*/models.py`).
Кардинальности используют нотацию «вороньей лапки» (Crow's Foot):
`||` — ровно один, `o{` — ноль или более, `o|` — ноль или один.

```mermaid
erDiagram
    User ||--|| Profile          : "имеет"
    User ||--o{ Deck             : "владеет"
    User ||--o{ ReviewLog        : "выполняет"
    Deck ||--o{ Card             : "содержит"
    Card ||--o{ ReviewLog        : "повторяется в"

    User {
        int       id              PK
        varchar   username        UK "уникальный логин"
        varchar   email
        varchar   password        "хэш PBKDF2-SHA256"
        datetime  date_joined
        bool      is_active
        bool      is_staff
        bool      is_superuser
    }

    Profile {
        int       id              PK
        int       user_id         FK,UK "1:1 с User"
        text      bio             "о себе"
        int       daily_new_cards_limit "по умолчанию 20"
        datetime  created_at
    }

    Deck {
        int       id              PK
        int       owner_id        FK "→ User.id"
        varchar   title           "макс. 200 символов"
        text      description
        bool      is_public
        datetime  created_at
        datetime  updated_at
    }

    Card {
        int       id              PK
        int       deck_id         FK "→ Deck.id"
        text      front           "вопрос"
        text      back            "ответ"
        datetime  created_at
    }

    ReviewLog {
        int       id              PK
        int       user_id         FK "→ User.id"
        int       card_id         FK "→ Card.id"
        smallint  quality         "0–5, оценка SM-2"
        float     easiness_factor "EF, ≥ 1.3"
        int       interval_days   "интервал I(n)"
        int       repetitions     "номер повторения n"
        date      next_review     "дата следующего показа"
        datetime  reviewed_at     "auto_now_add"
    }
```

## Описание связей

| Связь                       | Кардинальность | Семантика |
|-----------------------------|----------------|-----------|
| User — Profile              | 1 : 1          | У каждого пользователя ровно один профиль (создаётся при регистрации). |
| User — Deck                 | 1 : N          | Пользователь владеет произвольным числом колод. При удалении пользователя колоды каскадно удаляются (`on_delete=CASCADE`). |
| Deck — Card                 | 1 : N          | Колода содержит карточки. Удаление колоды каскадно удаляет карточки. |
| User — ReviewLog            | 1 : N          | Один пользователь генерирует множество записей повторений. |
| Card — ReviewLog            | 1 : N          | Одна карточка имеет историю повторений (по одному ReviewLog на каждый ответ). |

## Индексы

- `ReviewLog(user, next_review)` — выборка карточек, которые сегодня нужно повторить.
- `ReviewLog(user, card, -reviewed_at)` — поиск последнего ответа пользователя по конкретной карточке (используется при расчёте новых параметров SM-2).
- `User.username` — уникальный (стандартный Django).
- `Profile.user` — уникальный (OneToOneField).

## Как получить картинку для Word/ВКР

1. Открой https://mermaid.live
2. Скопируй блок ```mermaid ... ``` из этого файла (только содержимое, без обёртки)
3. Слева вставь, справа увидишь диаграмму
4. **Actions → Download SVG/PNG** → вставляй в Word

Альтернатива — в VS Code установить расширение «Markdown Preview Mermaid Support», открыть этот файл, сделать скриншот превью.

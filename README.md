# Library Management System

Веб-приложение для управления библиотечным фондом.

## Стек технологий

- **Python 3.12**
- **Flask** (Веб-фреймворк)
- **PostgreSQL** (База данных)
- **SQLAlchemy** (ORM)

## Архитектура

Проект построен по трехслойной архитектуре:

1.  **API Layer (`routes.py`)**: Принимает HTTP запросы, вызывает сервисы, возвращает HTML или JSON.
2.  **Service Layer (`services/`)**: Содержит всю бизнес-логику приложения.
3.  **Data Layer (`db/`, `models.py`)**: Отвечает за работу с базой данных.

## Установка и запуск

1.  **Клонировать репозиторий:**

    ```bash
    git clone https://github.com/Krame1S/python-library-management-system
    cd python-library-management-system
    ```

2.  **Создать и активировать виртуальное окружение:**

    Linux/macOS:

    ```bash
    python3 -m venv myenv
    source myenv/bin/activate
    ```

3.  **Установить зависимости:**

    ```bash
    pip install -r requirements.txt
    ```

4.  **Подготовить базу данных PostgreSQL:**

    Убедиться, что PostgreSQL установлен и запущен. Зайти в консоль `psql` и создать базу данных:

    ```sql
    CREATE DATABASE library;
    ```

5.  **Настроить конфигурацию (Обязательно):**

    Создать файл `.env` на основе примера:

    ```bash
    cp .env.example .env
    ```

    Открыть файл `.env` и изменить параметры подключения (`DB_USER`, `DB_PASSWORD`, `DB_NAME` и т.д.) на актуальные данные вашей PostgreSQL базы данных.
    
6.  **Запустить приложение:**
    ```bash
    python run.py
    ```
    Приложение будет доступно по адресу: `http://127.0.0.1:5000`

## Создание администратора

По умолчанию регистрация создает пользователя с правами `user`. Для назначения прав администратора необходимо выполнить SQL-запрос к базе данных.

1.  Зарегистрировать пользователя через веб-интерфейс по адресу `http://127.0.0.1:5000/register`.
2.  Выполнить SQL-запрос к вашей базе данных для смены роли:

```sql
UPDATE users
SET role = 'admin'
WHERE email = 'email@example.com';
```

def build_navigation(is_authenticated, is_admin, user_name=''):
    """Построить навигационное меню"""
    if not is_authenticated:
        return '''<nav>
        <a href="/">Главная</a> |
        <a href="/login">Войти</a> |
        <a href="/register">Регистрация</a>
    </nav>'''
    
    if is_admin:
        return f'''<nav>
        <a href="/">Главная</a> |
        <a href="/library">Библиотека</a> |
        <a href="/add-book">Добавить</a> |
        <a href="/issue-book">Выдать</a> |
        <a href="/reserve-book">Забронировать</a> |
        <a href="/management">Управление</a> |
        <a href="/logout">Выйти ({user_name})</a>
    </nav>'''
    
    return f'''<nav>
        <a href="/">Главная</a> |
        <a href="/library">Библиотека</a> |
        <a href="/profile">Мой кабинет</a> |
        <a href="/logout">Выйти ({user_name})</a>
    </nav>'''


def build_index_content(is_authenticated, is_admin, user_name=''):
    """Построить контент главной страницы"""
    if not is_authenticated:
        return '''<h2>Добро пожаловать в библиотечную систему</h2>
    <p>Для работы с системой необходимо <a href="/login">войти</a> или <a href="/register">зарегистрироваться</a></p>'''
    
    if is_admin:
        return f'''<h2>Добро пожаловать, {user_name}!</h2>
    
    <h3>Административная панель</h3>
    <ul>
        <li><a href="/library">Просмотреть все книги в библиотеке</a></li>
        <li><a href="/add-book">Добавить книгу в каталог</a></li>
        <li><a href="/issue-book">Выдать книгу читателю</a></li>
        <li><a href="/reserve-book">Забронировать книгу</a></li>
        <li><a href="/management">Управление записями (бронирования, выдачи, возвраты)</a></li>
    </ul>'''
    
    return f'''<h2>Добро пожаловать, {user_name}!</h2>
    
    <h3>Мои действия</h3>
    <ul>
        <li><a href="/library">Библиотека</a></li>
        <li><a href="/profile">Мой кабинет</a></li>
    </ul>'''


def build_books_table_for_library(books, is_admin):
    """Построить таблицу книг для страницы библиотеки"""
    if not books:
        if is_admin:
            return '<p>Библиотека пуста. <a href="/add-book">Добавьте книги</a>.</p>'
        return '<p>В библиотеке пока нет книг. Пожалуйста, обратитесь к администратору.</p>'
    
    rows = []
    for book in books:
        authors_str = ', '.join(book['authors']) if book['authors'] else '-'
        genres_str = ', '.join(book['genres']) if book['genres'] else '-'
        
        if book['copies'] > 0:
            status_text = f'✓ В наличии ({book["copies"]})'
        else:
            status_text = '✗ Нет в наличии'
        
        if is_admin:
            actions = f'''<a href="/edit-book/{book['isbn']}">Изменить</a> |
                <form method="POST" action="/delete-book" style="display: inline;">
                    <input type="hidden" name="isbn" value="{book['isbn']}">
                    <button type="submit" onclick="return confirm('Вы уверены?')">Удалить</button>
                </form>'''
        else:
            if book['copies'] > 0:
                actions = f'''<form method="POST" action="/reserve-book-user" style="display: inline;">
                    <input type="hidden" name="isbn" value="{book['isbn']}">
                    <button type="submit">Забронировать</button>
                </form>'''
            else:
                actions = '—'
        
        rows.append(f'''<tr>
            <td><strong>{book['title']}</strong></td>
            <td>{book['isbn']}</td>
            <td>{authors_str}</td>
            <td>{genres_str}</td>
            <td>{status_text}</td>
            <td>{actions}</td>
        </tr>''')
    
    return f'''<table border="1" cellpadding="5" cellspacing="0">
        <thead>
            <tr>
                <th>Название</th>
                <th>ISBN</th>
                <th>Авторы</th>
                <th>Жанры</th>
                <th>Статус</th>
                <th>Действия</th>
            </tr>
        </thead>
        <tbody>
            {''.join(rows)}
        </tbody>
    </table>'''


def build_status_select_options(current_status):
    """Построить опции выбора статуса"""
    statuses = [
        ('all', 'Все книги'),
        ('available', 'В наличии'),
        ('unavailable', 'Нет в наличии')
    ]
    
    options = []
    for value, label in statuses:
        selected = 'selected' if value == current_status else ''
        options.append(f'<option value="{value}" {selected}>{label}</option>')
    
    return '\n'.join(options)


def build_management_status_options(current_status):
    """Построить опции выбора статуса для управления"""
    statuses = [
        ('all', 'Все статусы'),
        ('reserved', 'Зарезервированные'),
        ('issued', 'Выданные'),
        ('returned', 'Возвращённые'),
        ('cancelled', 'Отменённые')
    ]
    
    options = []
    for value, label in statuses:
        selected = 'selected' if value == current_status else ''
        options.append(f'<option value="{value}" {selected}>{label}</option>')
    
    return '\n'.join(options)


def build_active_borrows_table(active_borrows):
    """Построить таблицу активных бронирований"""
    if not active_borrows:
        return '<p>У вас нет активных бронирований</p>'
    
    rows = []
    for record in active_borrows:
        status_text = 'Зарезервирована' if record['status'] == 'reserved' else 'Выдана'
        
        date = record.get('issue_date') or record.get('borrow_date', '-')
        expiry = record.get('reservation_expiry', '—')
        
        if record['status'] == 'issued':
            action_text = 'Отдать администратору'
        else:
            action_text = 'Ожидает выдачи'
        
        rows.append(f'''<tr>
            <td>{record['book_title']}</td>
            <td>{record['book_isbn']}</td>
            <td>{status_text}</td>
            <td>{date}</td>
            <td>{expiry}</td>
            <td>{action_text}</td>
        </tr>''')
    
    return f'''<table border="1" cellpadding="5" cellspacing="0">
        <thead>
            <tr>
                <th>Книга</th>
                <th>ISBN</th>
                <th>Статус</th>
                <th>Дата</th>
                <th>Истекает</th>
                <th>Действия</th>
            </tr>
        </thead>
        <tbody>
            {''.join(rows)}
        </tbody>
    </table>'''


def build_history_table(returned_records):
    """Построить таблицу истории возвратов"""
    if not returned_records:
        return '<p>История пуста</p>'
    
    rows = []
    for record in returned_records:
        rows.append(f'''<tr>
            <td>{record['book_title']}</td>
            <td>{record['book_isbn']}</td>
            <td>{record['borrow_date']}</td>
            <td>{record['return_date']}</td>
        </tr>''')
    
    return f'''<table border="1" cellpadding="5" cellspacing="0">
        <thead>
            <tr>
                <th>Книга</th>
                <th>ISBN</th>
                <th>Взята</th>
                <th>Возвращена</th>
            </tr>
        </thead>
        <tbody>
            {''.join(rows)}
        </tbody>
    </table>'''


def build_management_records_table(records):
    """Построить таблицу записей для страницы управления"""
    if not records:
        return '<p>Записи не найдены по выбранным фильтрам</p>'
    
    rows = []
    for record in records:
        actions = ''
        
        if record['status'] == 'reserved':
            actions = f'''<form method="POST" action="/issue-book-from-reservation" style="display: inline;">
                <input type="hidden" name="record_id" value="{record['id']}">
                <button type="submit">Выдать</button>
            </form>
            <form method="POST" action="/cancel-reservation" style="display: inline;">
                <input type="hidden" name="record_id" value="{record['id']}">
                <button type="submit" onclick="return confirm('Отменить резервацию?')">Отменить</button>
            </form>'''
        elif record['status'] == 'issued':
            actions = f'''<form method="POST" action="/mark-returned" style="display: inline;">
                <input type="hidden" name="record_id" value="{record['id']}">
                <input type="date" name="return_date" required>
                <button type="submit">Вернула</button>
            </form>
            <form method="POST" action="/cancel-issued" style="display: inline;">
                <input type="hidden" name="record_id" value="{record['id']}">
                <button type="submit" onclick="return confirm('Отменить выдачу и вернуть книгу?')">Отменить</button>
            </form>'''
        elif record['status'] == 'returned':
            actions = 'Завершено'
        elif record['status'] == 'cancelled':
            actions = 'Отменено'
        
        reservation_expiry = record.get('reservation_expiry', '-')
        issue_date = record.get('issue_date', '-')
        return_date = record.get('return_date', '-')
        
        rows.append(f'''<tr>
            <td>{record['book_title']}</td>
            <td>{record['book_isbn']}</td>
            <td>{record['user_full_name']}</td>
            <td>{record['user_email']}<br>{record['user_ticket']}</td>
            <td>{record['borrow_date']}</td>
            <td>{reservation_expiry}</td>
            <td>{issue_date}</td>
            <td>{return_date}</td>
            <td>{record['status']}</td>
            <td>{actions}</td>
        </tr>''')
    
    return f'''<table border="1" cellpadding="5" cellspacing="0">
        <thead>
            <tr>
                <th>Книга</th>
                <th>ISBN</th>
                <th>Читатель</th>
                <th>Email / Билет</th>
                <th>Дата брони</th>
                <th>Истекает</th>
                <th>Дата выдачи</th>
                <th>Дата возврата</th>
                <th>Статус</th>
                <th>Действия</th>
            </tr>
        </thead>
        <tbody>
            {''.join(rows)}
        </tbody>
    </table>'''


def build_google_books_results(books, query):
    """Построить результаты поиска Google Books"""
    if not books and not query:
        return ''
    
    if not books and query:
        return f'<p>Книги не найдены по запросу "{query}"</p>'
    
    results = [f'<h2>Результаты поиска ({len(books)} книг)</h2>']
    
    for book in books:
        authors_str = ', '.join(book.get('authors', [])) if book.get('authors') else '-'
        categories_str = ', '.join(book.get('categories', [])) if book.get('categories') else '-'
        
        if book['isbn'] != 'N/A':
            add_form = f'''<form method="POST" action="/import-book" style="display: inline;">
                <input type="hidden" name="isbn" value="{book['isbn']}">
                <label>Количество копий:</label>
                <input type="number" name="copies" value="1" min="1" max="100" size="3">
                <button type="submit">Добавить в библиотеку</button>
            </form>'''
        else:
            add_form = '<p><strong>ISBN отсутствует</strong> — невозможно добавить</p>'
        
        results.append(f'''<div style="border: 1px solid #ccc; padding: 10px; margin: 10px 0;">
            <h3>{book['title']}</h3>
            <p><strong>ISBN:</strong> {book['isbn']}</p>
            <p><strong>Авторы:</strong> {authors_str}</p>
            <p><strong>Категории:</strong> {categories_str}</p>
            <p><strong>Издатель:</strong> {book.get('publisher', 'Неизвестно')}</p>
            <p><strong>Дата публикации:</strong> {book.get('published_date', 'Неизвестно')}</p>
            <p><strong>Страниц:</strong> {book.get('page_count', 0)}</p>
            <p>{book.get('description', '')[:200]}</p>
            {add_form}
        </div>''')
    
    return '\n'.join(results)


def build_books_table_for_admin(books, query, action_url):
    """Построить таблицу книг для админа с кнопкой действия"""
    if not books and not query:
        return '<p>Введите поисковый запрос для поиска книг</p>'
    
    if not books and query:
        return f'<p>Доступные книги не найдены по запросу "{query}"</p>'
    
    rows = []
    for book in books:
        authors_str = ', '.join(book['authors']) if book['authors'] else '-'
        
        rows.append(f'''<tr>
            <td>{book['title']}</td>
            <td>{book['isbn']}</td>
            <td>{authors_str}</td>
            <td>{book['copies']}</td>
            <td><a href="{action_url}/{book['isbn']}">{action_url.split('/')[-1].capitalize()}</a></td>
        </tr>''')
    
    count = len(books)
    return f'''<h2>Доступные книги ({count})</h2>
    <table border="1" cellpadding="5" cellspacing="0">
        <thead>
            <tr>
                <th>Название</th>
                <th>ISBN</th>
                <th>Авторы</th>
                <th>Доступно</th>
                <th>Действия</th>
            </tr>
        </thead>
        <tbody>
            {''.join(rows)}
        </tbody>
    </table>'''


def build_user_reservations_table(user_reservations):
    """Построить таблицу резерваций пользователя"""
    if not user_reservations:
        return ''
    
    rows = []
    for res in user_reservations:
        rows.append(f'''<tr>
            <td>{res['book_title']}</td>
            <td>{res['book_isbn']}</td>
            <td>{res['status']}</td>
            <td>
                <form method="POST" action="/issue-book-from-reservation" style="display: inline;">
                    <input type="hidden" name="record_id" value="{res['id']}">
                    <button type="submit">Выдать</button>
                </form>
            </td>
        </tr>''')
    
    return f'''<hr>
    <h3>Зарезервированные книги этого пользователя</h3>
    <table border="1" cellpadding="5" cellspacing="0">
        <thead>
            <tr>
                <th>Книга</th>
                <th>ISBN</th>
                <th>Статус</th>
                <th>Действия</th>
            </tr>
        </thead>
        <tbody>
            {''.join(rows)}
        </tbody>
    </table>'''


def build_search_results(books, query):
    """Построить результаты поиска для пользователя"""
    if not books and not query:
        return '<p>Введите поисковый запрос для поиска книг в библиотеке</p>'
    
    if not books and query:
        return f'<p>Книги не найдены по запросу "{query}"</p>'
    
    results = [f'<h2>Результаты поиска ({len(books)} книг)</h2>']
    
    for book in books:
        authors_str = ', '.join(book['authors']) if book['authors'] else '-'
        genres_str = ', '.join(book['genres']) if book['genres'] else '-'
        
        if book['copies'] > 0:
            status_text = f'В наличии ({book["copies"]} экз.)'
            reserve_button = f'''<form method="POST" action="/reserve-book-user" style="display: inline;">
                <input type="hidden" name="isbn" value="{book['isbn']}">
                <button type="submit">Забронировать</button>
            </form>'''
        else:
            status_text = 'Нет в наличии'
            reserve_button = ''
        
        results.append(f'''<div>
            <h3>{book['title']}</h3>
            <p><strong>ISBN:</strong> {book['isbn']}</p>
            <p><strong>Авторы:</strong> {authors_str}</p>
            <p><strong>Жанры:</strong> {genres_str}</p>
            <p><strong>Статус:</strong> {status_text}</p>
            {reserve_button}
        </div>
        <hr>''')
    
    return '\n'.join(results)


def format_message(message):
    """Форматировать сообщение"""
    if not message:
        return ''
    return f'<p>{message}</p>'


def format_error(error):
    """Форматировать ошибку"""
    if not error:
        return ''
    return f'<p style="color: red;">Ошибка: {error}</p>'

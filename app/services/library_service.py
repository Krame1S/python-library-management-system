from app.db import db
from app.models import Book

class LibraryError(Exception):
    pass

class BookAlreadyExists(LibraryError):
    pass

class BookNotFound(LibraryError):
    pass

def get_books():
    return db.get_all_books()

def create_book(isbn, title, copies_available, author_names=None, genre_names=None):
    if not isbn or not title:
        raise LibraryError("ISBN and title are required")
    if len(title) > 30:
        raise LibraryError("Title must be 30 characters or less")
    if copies_available < 0:
        raise LibraryError("Copies available cannot be negative")
    if not isbn.isdigit() or len(isbn) != 13:
        raise LibraryError("ISBN must be 13 digits")
    if Book.query.get(isbn):
        raise BookAlreadyExists("ISBN already exists")
    db.add_book(isbn, title, copies_available, author_names, genre_names)

def update_book(isbn, title, copies_available, author_names=None, genre_names=None):
    if not isbn or not title:
        raise LibraryError("ISBN and title are required")
    if len(title) > 30:
        raise LibraryError("Title must be 30 chars or less")
    if copies_available < 0:
        raise LibraryError("Copies cannot be negative")
    if not isbn.isdigit() or len(isbn) != 13:
        raise LibraryError("ISBN must be 13 digits")
    if not Book.query.get(isbn):
        raise BookNotFound("Book not found")
    db.update_book(isbn, title, copies_available, author_names, genre_names)

def delete_book(isbn):
    if not isbn:
        raise LibraryError("ISBN is required")
    if not isbn.isdigit() or len(isbn) != 13:
        raise LibraryError("ISBN must be 13 digits")
    if not Book.query.get(isbn):
        raise BookNotFound("Book not found")
    db.delete_book(isbn)

def reserve_book(isbn, user_id, reservation_days=3):
    if not isbn or not user_id:
        raise LibraryError("ISBN and user_id are required")
    if not isbn.isdigit() or len(isbn) != 13:
        raise LibraryError("ISBN must be 13 digits")
    if not Book.query.get(isbn):
        raise BookNotFound("Book not found")

    try:
        record_id = db.reserve_book(isbn, user_id, reservation_days)
        return record_id
    except ValueError as e:
        raise LibraryError(str(e))

def issue_book(record_id):
    if not record_id:
        raise LibraryError("Record ID is required")

    try:
        return db.issue_book(record_id)
    except ValueError as e:
        raise LibraryError(str(e))

def cancel_reservation(record_id):
    if not record_id:
        raise LibraryError("Record ID is required")

    try:
        return db.cancel_reservation(record_id)
    except ValueError as e:
        raise LibraryError(str(e))

def return_book(isbn, user_id):
    if not isbn or not user_id:
        raise LibraryError("ISBN and user_id are required")
    if not isbn.isdigit() or len(isbn) != 13:
        raise LibraryError("ISBN must be 13 digits")
    if not Book.query.get(isbn):
        raise BookNotFound("Book not found")
    
    try:
        db.return_book(isbn, user_id)
    except ValueError as e:
        raise LibraryError(str(e))

def get_borrow_history(isbn=None, user_id=None):
    return db.get_borrow_history(isbn, user_id)

def get_active_borrows(user_id=None):
    return db.get_active_borrows(user_id)

def get_pending_reservations():
    return db.get_pending_reservations()

def cancel_expired_reservations():
    return db.cancel_expired_reservations()

def get_all_records():
    return db.get_all_records()


def search_books(query='', status_filter='all'):
    """Поиск и фильтрация книг"""
    books = get_books()
    
    if query:
        query_lower = query.lower()
        books = [b for b in books if (
            query_lower in b['title'].lower() or 
            query_lower in b['isbn'] or
            any(query_lower in author.lower() for author in b['authors'])
        )]
    
    if status_filter == 'available':
        books = [b for b in books if b['copies'] > 0]
    elif status_filter == 'unavailable':
        books = [b for b in books if b['copies'] == 0]
    
    return books


def get_library_stats(all_books):
    """Получить статистику по библиотеке"""
    available_count = sum(1 for book in all_books if book['copies'] > 0)
    total_count = len(all_books)
    return {
        'available': available_count,
        'total': total_count
    }


def prepare_profile_data(user_id):
    """Подготовить данные для профиля пользователя"""
    active_borrows = get_active_borrows(user_id)
    history = get_borrow_history(user_id=user_id)
    
    returned_records = [r for r in history if r['status'] == 'returned']
    
    return {
        'active_borrows': active_borrows,
        'returned_records': returned_records[:10]
    }


def filter_records(all_records, status_filter='all', user_email='', user_ticket=''):
    """Фильтрация записей по параметрам"""
    filtered = []
    
    for record in all_records:
        if status_filter != 'all' and record.get('status') != status_filter:
            continue
        if user_email and user_email.lower() not in record.get('user_email', '').lower():
            continue
        if user_ticket and user_ticket not in record.get('user_ticket', ''):
            continue
        
        filtered.append(record)
    
    return filtered


def return_book_by_record(record_id, return_date):
    """Вернуть книгу по ID записи"""
    from app.models import BorrowRecord, db as models_db
    from datetime import datetime
    
    record = BorrowRecord.query.get(record_id)
    if not record:
        raise LibraryError("Запись не найдена")
    
    record.status = 'returned'
    record.return_date = datetime.strptime(return_date, '%Y-%m-%d').date()
    
    book = record.book
    book.copies_available += 1
    
    models_db.session.commit()


def cancel_issued_book(record_id):
    """Отменить выданную книгу"""
    from app.models import BorrowRecord, db as models_db
    
    record = BorrowRecord.query.get(record_id)
    if not record:
        raise LibraryError("Запись не найдена")
    
    if record.status != 'issued':
        raise LibraryError("Можно отменить только выданные книги")
    
    record.status = 'cancelled'
    book = record.book
    book.copies_available += 1
    
    models_db.session.commit()
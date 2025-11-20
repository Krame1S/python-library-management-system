from app.models import db, Book, Author, Genre, BorrowRecord
from datetime import date, timedelta

def get_all_books():
    return [book.to_dict() for book in Book.query.all()]

def add_book(isbn, title, copies_available, author_names=None, genre_names=None):
    book = Book(isbn=isbn, title=title, copies_available=copies_available)
    if author_names:
        for name in author_names:
            author = Author.query.filter_by(name=name).first() or Author(name=name)
            book.authors.append(author)
    if genre_names:
        for name in genre_names:
            genre = Genre.query.filter_by(name=name).first() or Genre(name=name)
            book.genres.append(genre)
    db.session.add(book)
    db.session.commit()

def update_book(isbn, title, copies_available, author_names=None, genre_names=None):
    book = Book.query.get(isbn)
    if not book:
        raise ValueError("Book not found")
    book.title = title
    book.copies_available = copies_available
    if author_names:
        book.authors = [Author.query.filter_by(name=name).first() or Author(name=name) for name in author_names]
    if genre_names:
        book.genres = [Genre.query.filter_by(name=name).first() or Genre(name=name) for name in genre_names]
    db.session.commit()

def delete_book(isbn):
    book = Book.query.get(isbn)
    if not book:
        raise ValueError("Book not found")
    db.session.delete(book)
    db.session.commit()

def reserve_book(isbn, user_id, reservation_days=3):
    book = Book.query.get(isbn)
    if not book:
        raise ValueError("Book not found")
    if book.copies_available <= 0:
        raise ValueError("No copies available")

    reservation_expiry = date.today() + timedelta(days=reservation_days)
    borrow_record = BorrowRecord(
        book_isbn=isbn,
        user_id=user_id,
        reservation_expiry=reservation_expiry,
        status='reserved'
    )
    book.copies_available -= 1
    db.session.add(borrow_record)
    db.session.commit()
    return borrow_record.id

def issue_book(record_id):
    borrow_record = BorrowRecord.query.get(record_id)
    if not borrow_record:
        raise ValueError("Borrow record not found")
    if borrow_record.status != 'reserved':
        raise ValueError("Book is not in reserved status")

    borrow_record.status = 'issued'
    borrow_record.issue_date = date.today()
    borrow_record.reservation_expiry = None   
    db.session.commit()
    return borrow_record.id

def cancel_reservation(record_id):
    borrow_record = BorrowRecord.query.get(record_id)
    if not borrow_record:
        raise ValueError("Borrow record not found")
    if borrow_record.status not in ['reserved', 'issued']:
        raise ValueError("Cannot cancel this record")

    borrow_record.status = 'cancelled'
    # Вернуть копию в фонд
    book = Book.query.get(borrow_record.book_isbn)
    book.copies_available += 1
    db.session.commit()
    return borrow_record.id

def return_book(isbn, user_id):
    from datetime import date
    borrow_record = BorrowRecord.query.filter_by(
        book_isbn=isbn,
        user_id=user_id,
        status='issued'
    ).first()

    if not borrow_record:
        raise ValueError("No active issued record found")

    book = Book.query.get(isbn)
    borrow_record.return_date = date.today()
    borrow_record.status = 'returned'
    book.copies_available += 1
    db.session.commit()

def get_borrow_history(isbn=None, user_id=None):
    query = BorrowRecord.query
    if isbn:
        query = query.filter_by(book_isbn=isbn)
    if user_id:
        query = query.filter_by(user_id=user_id)

    records = query.all()
    return [{
        'id': r.id,
        'book_isbn': r.book_isbn,
        'book_title': r.book.title,
        'user_id': r.user_id,
        'borrow_date': r.borrow_date.isoformat(),
        'reservation_expiry': r.reservation_expiry.isoformat() if r.reservation_expiry else None,
        'issue_date': r.issue_date.isoformat() if r.issue_date else None,
        'return_date': r.return_date.isoformat() if r.return_date else None,
        'status': r.status
    } for r in records]

def get_active_borrows(user_id=None):
    query = BorrowRecord.query.filter(BorrowRecord.status.in_(['reserved', 'issued']))
    if user_id:
        query = query.filter_by(user_id=user_id)

    records = query.all()
    return [{
        'id': r.id,
        'book_isbn': r.book_isbn,
        'book_title': r.book.title,
        'user_id': r.user_id,
        'borrow_date': r.borrow_date.isoformat(),
        'reservation_expiry': r.reservation_expiry.isoformat() if r.reservation_expiry else None,
        'issue_date': r.issue_date.isoformat() if r.issue_date else None,
        'status': r.status
    } for r in records]

def get_pending_reservations():
    """Get reservations that need admin action"""
    query = BorrowRecord.query.filter_by(status='reserved')
    records = query.all()
    return [{
        'id': r.id,
        'book_isbn': r.book_isbn,
        'book_title': r.book.title,
        'user_id': r.user_id,
        'user_full_name': r.user.full_name,
        'borrow_date': r.borrow_date.isoformat(),
        'reservation_expiry': r.reservation_expiry.isoformat() if r.reservation_expiry else None
    } for r in records]

def cancel_expired_reservations():
    """Cancel reservations that have expired"""
    today = date.today()
    expired_records = BorrowRecord.query.filter(
        BorrowRecord.status == 'reserved',
        BorrowRecord.reservation_expiry < today
    ).all()

    cancelled_count = 0
    for record in expired_records:
        record.status = 'cancelled'
        book = Book.query.get(record.book_isbn)
        book.copies_available += 1
        cancelled_count += 1

    db.session.commit()
    return cancelled_count

def get_all_records():
    from sqlalchemy.orm import joinedload
    
    records = BorrowRecord.query.options(
        joinedload(BorrowRecord.book),
        joinedload(BorrowRecord.user)
    ).all()
    
    return [{
        'id': r.id,
        'book_isbn': r.book_isbn,
        'book_title': r.book.title,
        'user_id': r.user_id,
        'user_email': r.user.email,
        'user_ticket': r.user.ticket_number or '-',
        'user_full_name': r.user.full_name,
        'borrow_date': r.borrow_date.isoformat(),
        'reservation_expiry': r.reservation_expiry.isoformat() if r.reservation_expiry else None,
        'issue_date': r.issue_date.isoformat() if r.issue_date else None,
        'return_date': r.return_date.isoformat() if r.return_date else None,
        'status': r.status
    } for r in records]
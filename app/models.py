from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import date

db = SQLAlchemy()

book_authors = db.Table('book_authors',
    db.Column('book_isbn', db.String(13), db.ForeignKey('books.isbn'), primary_key=True),
    db.Column('author_id', db.Integer, db.ForeignKey('authors.id'), primary_key=True)
)

book_genres = db.Table('book_genres',
    db.Column('book_isbn', db.String(13), db.ForeignKey('books.isbn'), primary_key=True),
    db.Column('genre_id', db.Integer, db.ForeignKey('genres.id'), primary_key=True)
)

class Book(db.Model):
    __tablename__ = 'books'
    isbn = db.Column(db.String(13), primary_key=True)
    title = db.Column(db.String(30), nullable=False)
    copies_available = db.Column(db.Integer, nullable=False, default=1)
    authors = db.relationship('Author', secondary=book_authors, backref='books')
    genres = db.relationship('Genre', secondary=book_genres, backref='books')

    def to_dict(self):
        return {
            'isbn': self.isbn,
            'title': self.title,
            'copies': self.copies_available,
            'authors': [author.name for author in self.authors],
            'genres': [genre.name for genre in self.genres]
        }

class Author(db.Model):
    __tablename__ = 'authors'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)

class Genre(db.Model):
    __tablename__ = 'genres'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(30), nullable=False)

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    ticket_number = db.Column(db.String(20), unique=True, nullable=True)  # Номер читательского билета
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=True)  # Пароль может быть пустым для новых пользователей
    full_name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='user')
    created_at = db.Column(db.Date, nullable=False, default=date.today)
    is_active = db.Column(db.Boolean, default=True)
    
    def set_password(self, password):
        if password:
            self.password_hash = generate_password_hash(password)
        else:
            self.password_hash = None

    def check_password(self, password):
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)
    
    def is_admin(self):
        return self.role == 'admin'

class BorrowRecord(db.Model):
    __tablename__ = 'borrow_records'
    id = db.Column(db.Integer, primary_key=True)
    book_isbn = db.Column(db.String(13), db.ForeignKey('books.isbn'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    borrow_date = db.Column(db.Date, nullable=False, default=date.today)  # Дата резервации
    reservation_expiry = db.Column(db.Date, nullable=True)  # Срок резервации
    issue_date = db.Column(db.Date, nullable=True)  # Дата фактической выдачи
    return_date = db.Column(db.Date, nullable=True)  # Дата возврата
    status = db.Column(db.String(20), nullable=False, default='reserved')  # reserved, issued, returned, cancelled
    book = db.relationship('Book', backref='borrow_records')
    user = db.relationship('User', backref='borrow_records')
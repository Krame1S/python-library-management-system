from app.models import db, User
import random
import string


def find_user_by_identifier(identifier):
    """Найти пользователя по email или номеру билета"""
    if not identifier:
        return None
    user = User.query.filter(
        (User.email == identifier) | (User.ticket_number == identifier)
    ).first()
    return user


def create_reader(email, full_name):
    """Создать нового читателя с временным паролем"""
    import random
    import string
    
    temp_password = ''.join(random.choices(string.digits, k=6))
    
    user = User(email=email, full_name=full_name, role='user')
    user.ticket_number = generate_ticket_number()
    user.set_password(temp_password)
    
    db.session.add(user)
    db.session.commit()
    
    return user, temp_password


def check_user_exists(email):
    """Проверить существование пользователя по email"""
    return User.query.filter_by(email=email).first() is not None


def generate_ticket_number():
    """Сгенерировать уникальный номер читательского билета"""
    while True:
        ticket = ''.join(random.choices(string.digits, k=8))
        if not User.query.filter_by(ticket_number=ticket).first():
            return ticket

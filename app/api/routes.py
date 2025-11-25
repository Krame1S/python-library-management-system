from flask import jsonify, request, render_template, redirect, url_for, flash, session
from flask_login import login_user, logout_user, login_required, current_user
from functools import wraps
from app.models import db, User
from app.services import library_service, google_books_service, user_service

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin():
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

def admin_api_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin():
            return jsonify({'error': 'Forbidden: Admin access required'}), 403
        return f(*args, **kwargs)
    return decorated_function

def register_routes(app):
    @app.route('/')
    def index():
        return render_template('index.html')
    
    @app.route('/register', methods=['GET', 'POST'])
    def register():
        if current_user.is_authenticated:
            return redirect(url_for('index'))
        
        if request.method == 'POST':
            email = request.form.get('email')
            full_name = request.form.get('full_name')
            password = request.form.get('password')
            password_confirm = request.form.get('password_confirm')
            
            if password != password_confirm:
                flash('Пароли не совпадают', 'error')
                return render_template('register.html')
            
            if user_service.check_user_exists(email):
                flash('Email уже зарегистрирован', 'error')
                return render_template('register.html')
            
            user = User(email=email, full_name=full_name, role='user')
            user.set_password(password)
            user.ticket_number = user_service.generate_ticket_number()
            db.session.add(user)
            db.session.commit()
            
            login_user(user)
            return redirect(url_for('index'))
        
        return render_template('register.html')
    
    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if current_user.is_authenticated:
            return redirect(url_for('index'))
        
        if request.method == 'POST':
            email = request.form.get('email')
            password = request.form.get('password')
            
            user = User.query.filter_by(email=email).first()
            
            if not user or not user.check_password(password):
                flash('Неверный email или пароль', 'error')
                return render_template('login.html')
            
            login_user(user)
            return redirect(url_for('index'))
        
        return render_template('login.html')
    
    @app.route('/logout')
    @login_required
    def logout():
        logout_user()
        return redirect(url_for('index'))
    
    @app.route('/profile')
    @login_required
    def profile():
        profile_data = library_service.prepare_profile_data(current_user.id)
        return render_template('profile.html',
                             active_borrows=profile_data['active_borrows'],
                             history=profile_data['returned_records'])

    @app.route('/search')
    def search_page():
        query = request.args.get('query', '')
        books = library_service.search_books(query=query)
        return render_template('search.html', query=query, books=books)

    @app.route('/import-book', methods=['POST'])
    @login_required
    @admin_required
    def import_book():
        isbn = request.form.get('isbn')
        copies = request.form.get('copies', 1, type=int)
        
        try:
            book_data = google_books_service.get_book_by_isbn(isbn)
            if not book_data:
                flash('Книга не найдена', 'error')
                return redirect(url_for('search_page'))
            
            library_service.create_book(
                isbn=book_data['isbn'],
                title=book_data['title'],
                copies_available=copies,
                author_names=book_data.get('authors', []),
                genre_names=book_data.get('categories', [])
            )
            flash('Книга успешно добавлена', 'success')
            return redirect(url_for('library_page'))
        except library_service.BookAlreadyExists:
            flash('Книга уже существует в библиотеке', 'error')
            return redirect(url_for('library_page'))
        except Exception as e:
            flash(str(e), 'error')
            return redirect(url_for('library_page'))

    @app.route('/library')
    @login_required
    def library_page():
        all_books = library_service.get_books()
        query = request.args.get('query', '')
        status_filter = request.args.get('status', 'all')
        
        books = library_service.search_books(query, status_filter)
        stats = library_service.get_library_stats(all_books)
        
        return render_template('library.html',
                             total_books=stats['total'],
                             query=query,
                             status_filter=status_filter,
                             result_count=len(books),
                             available_books=stats['available'],
                             books=books)

    @app.route('/add-book', methods=['GET', 'POST'])
    @login_required
    @admin_required
    def add_book_page():
        query = request.args.get('query', '')
        
        if request.method == 'POST' and 'isbn' in request.form:
            isbn = request.form.get('isbn')
            title = request.form.get('title')
            copies = request.form.get('copies', 1, type=int)
            authors = list(set([a.strip() for a in request.form.get('authors', '').split(',') if a.strip()]))
            genres = list(set([g.strip() for g in request.form.get('genres', '').split(',') if g.strip()]))
            
            try:
                library_service.create_book(isbn, title, copies, authors, genres)
                flash('Книга успешно добавлена', 'success')
                return redirect(url_for('library_page'))
            except Exception as e:
                flash(str(e), 'error')
        
        google_books = []
        if query:
            try:
                google_books = google_books_service.search_books(query)
            except Exception as e:
                flash(str(e), 'error')
        
        return render_template('add_book.html',
                             query=query,
                             google_books=google_books)

    @app.route('/issue-book')
    @login_required
    @admin_required
    def issue_book_page():
        query = request.args.get('query', '')
        books = library_service.search_books(query=query, status_filter='available')
        return render_template('issue_book.html', query=query, books=books)

    @app.route('/issue-book/<isbn>', methods=['GET', 'POST'])
    @login_required
    @admin_required
    def issue_book_confirm(isbn):
        all_books = library_service.get_books()
        book = next((b for b in all_books if b['isbn'] == isbn), None)
        if not book:
            flash('Книга не найдена', 'error')
            return redirect(url_for('issue_book_page'))

        user_reservations = []

        if request.method == 'POST':
            user_identifier = request.form.get('user_identifier')
            if user_identifier:
                user = user_service.find_user_by_identifier(user_identifier)

                if not user:
                    flash('Читатель не найден', 'error')
                else:
                    try:
                        record_id = library_service.reserve_book(isbn, user.id)
                        library_service.issue_book(record_id)
                        flash(f'Книга выдана пользователю {user.full_name}', 'success')
                        return redirect(url_for('management_page'))
                    except Exception as e:
                        flash(str(e), 'error')
                        active = library_service.get_active_borrows(user.id)
                        user_reservations = [r for r in active if r['status'] == 'reserved']

        return render_template('issue_confirm.html',
                             book=book,
                             user_reservations=user_reservations)

    @app.route('/issue-book-from-reservation', methods=['POST'])
    @login_required
    @admin_required
    def issue_book_from_reservation():
        record_id = request.form.get('record_id', type=int)
        
        try:
            library_service.issue_book(record_id)
            flash('Книга выдана', 'success')
            return redirect(url_for('management_page'))
        except Exception as e:
            flash(str(e), 'error')
            return redirect(url_for('management_page'))
    
    @app.route('/register-user-for-issue', methods=['POST'])
    @login_required
    @admin_required
    def register_user_for_issue():
        isbn = request.form.get('isbn')
        full_name = request.form.get('full_name')
        email = request.form.get('email')

        if user_service.check_user_exists(email):
            flash('Пользователь с таким email уже существует', 'error')
            return redirect(url_for('issue_book_confirm', isbn=isbn))

        user, temp_password = user_service.create_reader(email, full_name)

        try:
            record_id = library_service.reserve_book(isbn, user.id)
            library_service.issue_book(record_id)
            session['new_user_data'] = {
                'ticket': user.ticket_number,
                'temp_password': temp_password,
                'full_name': user.full_name
            }
            flash(f'Новый пользователь {user.full_name} зарегистрирован. Книга выдана.', 'success')
            return redirect(url_for('issue_book_confirm', isbn=isbn))
        except Exception as e:
            flash(str(e), 'error')
            return redirect(url_for('management_page'))

    @app.route('/reserve-book')
    @login_required
    @admin_required
    def reserve_book_page():
        query = request.args.get('query', '')
        books = library_service.search_books(query=query, status_filter='available')
        return render_template('reserve_book.html', query=query, books=books)

    @app.route('/reserve-book/<isbn>', methods=['GET', 'POST'])
    @login_required
    @admin_required
    def reserve_book_confirm(isbn):
        all_books = library_service.get_books()
        book = next((b for b in all_books if b['isbn'] == isbn), None)
        if not book:
            flash('Книга не найдена', 'error')
            return redirect(url_for('reserve_book_page'))

        if request.method == 'POST':
            user_identifier = request.form.get('user_identifier')
            if user_identifier:
                user = user_service.find_user_by_identifier(user_identifier)

                if not user:
                    flash('Читатель не найден', 'error')
                else:
                    try:
                        library_service.reserve_book(isbn, user.id)
                        flash(f'Книга забронирована для пользователя {user.full_name}', 'success')
                        return redirect(url_for('management_page'))
                    except Exception as e:
                        flash(str(e), 'error')

        return render_template('reserve_confirm.html', book=book)

    @app.route('/register-user-for-reserve', methods=['POST'])
    @login_required
    @admin_required
    def register_user_for_reserve():
        isbn = request.form.get('isbn')
        full_name = request.form.get('full_name')
        email = request.form.get('email')

        if user_service.check_user_exists(email):
            flash('Пользователь с таким email уже существует', 'error')
            return redirect(url_for('reserve_book_confirm', isbn=isbn))

        user, temp_password = user_service.create_reader(email, full_name)

        try:
            library_service.reserve_book(isbn, user.id)
            session['new_user_data'] = {
                'ticket': user.ticket_number,
                'temp_password': temp_password,
                'full_name': user.full_name
            }
            flash(f'Новый пользователь {user.full_name} зарегистрирован. Книга забронирована.', 'success')
            return redirect(url_for('reserve_book_confirm', isbn=isbn))
        except Exception as e:
            flash(str(e), 'error')
            return redirect(url_for('management_page'))

    @app.route('/edit-book/<isbn>')
    @login_required
    @admin_required
    def edit_book_page(isbn):
        all_books = library_service.get_books()
        book = next((b for b in all_books if b['isbn'] == isbn), None)
        if not book:
            flash('Книга не найдена', 'error')
            return redirect(url_for('management_page'))
        
        return render_template('edit_book.html', book=book)

    @app.route('/update-book', methods=['POST'])
    @login_required
    @admin_required
    def update_book():
        isbn = request.form.get('isbn')
        title = request.form.get('title')
        copies = request.form.get('copies', 1, type=int)
        authors = list(set([a.strip() for a in request.form.get('authors', '').split(',') if a.strip()]))
        genres = list(set([g.strip() for g in request.form.get('genres', '').split(',') if g.strip()]))
        
        try:
            library_service.update_book(isbn, title, copies, authors, genres)
            flash('Книга успешно обновлена', 'success')
            return redirect(url_for('library_page'))
        except Exception as e:
            flash(str(e), 'error')
            return redirect(url_for('library_page'))

    @app.route('/delete-book', methods=['POST'])
    @login_required
    @admin_required
    def delete_book():
        isbn = request.form.get('isbn')
        try:
            library_service.delete_book(isbn)
            flash('Книга успешно удалена', 'success')
            return redirect(url_for('library_page'))
        except Exception as e:
            flash(str(e), 'error')
            return redirect(url_for('library_page'))

    @app.route('/mark-returned', methods=['POST'])
    @login_required
    @admin_required
    def mark_returned():
        record_id = request.form.get('record_id', type=int)
        return_date_str = request.form.get('return_date')
        
        try:
            library_service.return_book_by_record(record_id, return_date_str)
            flash('Книга отмечена как возвращенная', 'success')
            return redirect(url_for('management_page'))
        except Exception as e:
            flash(str(e), 'error')
            return redirect(url_for('management_page'))
    
    @app.route('/cancel-issued', methods=['POST'])
    @login_required
    @admin_required
    def cancel_issued():
        record_id = request.form.get('record_id', type=int)
        
        try:
            library_service.cancel_issued_book(record_id)
            flash('Выдача отменена, книга возвращена в фонд', 'success')
            return redirect(url_for('management_page'))
        except Exception as e:
            flash(str(e), 'error')
            return redirect(url_for('management_page'))

    @app.route('/reserve-book-user', methods=['POST'])
    @login_required
    def reserve_book_user():
        isbn = request.form.get('isbn')
        user_id = current_user.id

        try:
            library_service.reserve_book(isbn, user_id)
            flash('Книга успешно зарезервирована', 'success')
            return redirect(url_for('profile'))
        except Exception as e:
            flash(str(e), 'error')
            return redirect(url_for('profile'))

    @app.route('/cancel-reservation', methods=['POST'])
    @login_required
    @admin_required
    def cancel_reservation():
        record_id = request.form.get('record_id', type=int)

        try:
            library_service.cancel_reservation(record_id)
            flash('Резервация отменена', 'success')
            return redirect(url_for('management_page'))
        except Exception as e:
            flash(str(e), 'error')
            return redirect(url_for('management_page'))

    @app.route('/management')
    @login_required
    @admin_required
    def management_page():
        status_filter = request.args.get('status', 'all')
        user_email = request.args.get('user_email', '')
        user_ticket = request.args.get('user_ticket', '')
        
        try:
            all_records = library_service.get_all_records()
            records = library_service.filter_records(all_records, status_filter, user_email, user_ticket)
        except Exception as e:
            records = []
            flash(str(e), 'error')
        
        return render_template('management.html',
                             status_filter=status_filter,
                             user_email=user_email,
                             user_ticket=user_ticket,
                             records=records)

    # API endpoints
    @app.route('/api/v1/books', methods=['GET'])
    @login_required
    @admin_api_required
    def get_books():
        return jsonify({'books': library_service.get_books()}), 200

    @app.route('/api/v1/books', methods=['POST'])
    @login_required
    @admin_api_required
    def create_book():
        try:
            data = request.get_json()
            isbn = data.get('isbn')
            title = data.get('title')
            copies = data.get('copies', 1)
            authors = data.get('authors', [])
            genres = data.get('genres', [])
            library_service.create_book(isbn, title, copies, authors, genres)
            return jsonify({'message': 'Book created successfully'}), 201
        except library_service.BookAlreadyExists as e:
            return jsonify({'error': str(e)}), 409
        except library_service.LibraryError as e:
            return jsonify({'error': str(e)}), 400
        except Exception:
            return jsonify({'error': 'Server error'}), 500

    @app.route('/api/v1/books/<isbn>', methods=['PUT'])
    @login_required
    @admin_api_required
    def update_book_api(isbn):
        try:
            data = request.get_json()
            title = data.get('title')
            copies = data.get('copies', 1)
            authors = data.get('authors', [])
            genres = data.get('genres', [])
            library_service.update_book(isbn, title, copies, authors, genres)
            return jsonify({'message': 'Book updated successfully'}), 200
        except library_service.BookNotFound as e:
            return jsonify({'error': str(e)}), 404
        except library_service.LibraryError as e:
            return jsonify({'error': str(e)}), 400
        except Exception:
            return jsonify({'error': 'Server error'}), 500

    @app.route('/api/v1/books/<isbn>', methods=['DELETE'])
    @login_required
    @admin_api_required
    def delete_book_api(isbn):
        try:
            library_service.delete_book(isbn)
            return jsonify({'message': 'Book deleted successfully'}), 200
        except library_service.BookNotFound as e:
            return jsonify({'error': str(e)}), 404
        except library_service.LibraryError as e:
            return jsonify({'error': str(e)}), 400
        except Exception:
            return jsonify({'error': 'Server error'}), 500

    @app.route('/api/v1/borrow-history', methods=['GET'])
    @login_required
    def get_borrow_history():
        try:
            isbn = request.args.get('isbn')
            user_id = request.args.get('user_id')
            
            # Обычный пользователь может видеть только свою историю
            if not current_user.is_admin():
                if user_id and int(user_id) != current_user.id:
                    return jsonify({'error': 'Forbidden'}), 403
                user_id = current_user.id
            else:
                # Если админ не указал user_id, показать его собственную историю
                if not user_id:
                    user_id = current_user.id
            
            history = library_service.get_borrow_history(isbn, user_id)
            return jsonify({'history': history}), 200
        except Exception:
            return jsonify({'error': 'Server error'}), 500

    @app.route('/api/v1/active-borrows', methods=['GET'])
    @login_required
    def get_active_borrows():
        try:
            user_id = request.args.get('user_id')
            
            # Обычный пользователь может видеть только свои данные
            if not current_user.is_admin():
                if user_id and int(user_id) != current_user.id:
                    return jsonify({'error': 'Forbidden'}), 403
                user_id = current_user.id
            else:
                # Если админ не указал user_id, показать его собственные бронирования
                if not user_id:
                    user_id = current_user.id

            active_borrows = library_service.get_active_borrows(user_id)
            return jsonify({'active_borrows': active_borrows}), 200
        except Exception:
            return jsonify({'error': 'Server error'}), 500

    @app.route('/api/v1/search/google-books', methods=['GET'])
    @login_required
    @admin_api_required
    def search_google_books():
        try:
            query = request.args.get('query', '')
            max_results = request.args.get('max_results', 10, type=int)
            
            if not query:
                return jsonify({'error': 'Query parameter is required'}), 400
            
            books = google_books_service.search_books(query, max_results)
            return jsonify({'books': books}), 200
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/v1/search/google-books/isbn/<isbn>', methods=['GET'])
    @login_required
    @admin_api_required
    def get_google_book_by_isbn(isbn):
        try:
            book = google_books_service.get_book_by_isbn(isbn)
            if not book:
                return jsonify({'error': 'Book not found'}), 404
            return jsonify(book), 200
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/v1/import/google-books', methods=['POST'])
    @login_required
    @admin_api_required
    def import_from_google_books():
        try:
            data = request.get_json()
            isbn = data.get('isbn')
            copies = data.get('copies', 1)
            
            if not isbn:
                return jsonify({'error': 'ISBN is required'}), 400
            
            book_data = google_books_service.get_book_by_isbn(isbn)
            if not book_data:
                return jsonify({'error': 'Book not found in Google Books'}), 404
            
            library_service.create_book(
                isbn=book_data['isbn'],
                title=book_data['title'],
                copies_available=copies,
                author_names=book_data.get('authors', []),
                genre_names=book_data.get('categories', [])
            )
            
            return jsonify({'message': 'Book imported successfully'}), 201
        except library_service.BookAlreadyExists as e:
            return jsonify({'error': str(e)}), 409
        except library_service.LibraryError as e:
            return jsonify({'error': str(e)}), 400
        except Exception as e:
            return jsonify({'error': str(e)}), 500

from flask import jsonify, request, render_template, redirect, url_for
from flask_login import login_user, logout_user, login_required, current_user
from functools import wraps
from app.models import db, User
from app.services import library_service, google_books_service, user_service, presentation_service

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin():
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

def register_routes(app):
    @app.route('/')
    def index():
        is_authenticated = current_user.is_authenticated
        is_admin = current_user.is_admin() if is_authenticated else False
        user_name = current_user.full_name if is_authenticated else ''
        
        navigation = presentation_service.build_navigation(is_authenticated, is_admin, user_name)
        content = presentation_service.build_index_content(is_authenticated, is_admin, user_name)
        
        return render_template('index.html', navigation=navigation, content=content)
    
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
                error_html = presentation_service.format_error('Пароли не совпадают')
                return render_template('register.html', error=error_html)
            
            if user_service.check_user_exists(email):
                error_html = presentation_service.format_error('Email уже зарегистрирован')
                return render_template('register.html', error=error_html)
            
            user = User(email=email, full_name=full_name, role='user')
            user.set_password(password)
            user.ticket_number = user_service.generate_ticket_number()
            db.session.add(user)
            db.session.commit()
            
            login_user(user)
            return redirect(url_for('index'))
        
        return render_template('register.html', error='')
    
    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if current_user.is_authenticated:
            return redirect(url_for('index'))
        
        if request.method == 'POST':
            email = request.form.get('email')
            password = request.form.get('password')
            
            user = User.query.filter_by(email=email).first()
            
            if not user or not user.check_password(password):
                error_html = presentation_service.format_error('Неверный email или пароль')
                return render_template('login.html', error=error_html)
            
            login_user(user)
            return redirect(url_for('index'))
        
        return render_template('login.html', error='')
    
    @app.route('/logout')
    @login_required
    def logout():
        logout_user()
        return redirect(url_for('index'))
    
    @app.route('/profile')
    @login_required
    def profile():
        is_admin = current_user.is_admin()
        user_name = current_user.full_name
        
        navigation = presentation_service.build_navigation(True, is_admin, user_name)
        
        profile_data = library_service.prepare_profile_data(current_user.id)
        
        active_borrows_table = presentation_service.build_active_borrows_table(profile_data['active_borrows'])
        history_table = presentation_service.build_history_table(profile_data['returned_records'])
        
        user_ticket_html = ''
        if current_user.ticket_number:
            user_ticket_html = f'<p><strong>Номер читательского билета:</strong> {current_user.ticket_number}</p>'
        
        message = presentation_service.format_message(request.args.get('message'))
        error = presentation_service.format_error(request.args.get('error'))
        
        return render_template('profile.html',
                             navigation=navigation,
                             user_name=user_name,
                             user_email=current_user.email,
                             user_ticket_html=user_ticket_html,
                             user_created=current_user.created_at,
                             active_borrows_table=active_borrows_table,
                             history_table=history_table,
                             message=message,
                             error=error)

    @app.route('/search')
    def search_page():
        query = request.args.get('query', '')
        is_authenticated = current_user.is_authenticated
        is_admin = current_user.is_admin() if is_authenticated else False
        user_name = current_user.full_name if is_authenticated else ''
        
        navigation = presentation_service.build_navigation(is_authenticated, is_admin, user_name)
        
        books = library_service.search_books(query=query)
        search_results = presentation_service.build_search_results(books, query)
        
        error = presentation_service.format_error(request.args.get('error'))
        message = presentation_service.format_message(request.args.get('message'))
        
        return render_template('search.html',
                             navigation=navigation,
                             query=query,
                             search_results=search_results,
                             error=error,
                             message=message)

    @app.route('/import-book', methods=['POST'])
    @login_required
    @admin_required
    def import_book():
        isbn = request.form.get('isbn')
        copies = request.form.get('copies', 1, type=int)
        
        try:
            book_data = google_books_service.get_book_by_isbn(isbn)
            if not book_data:
                return redirect(url_for('search_page', error='Книга не найдена'))
            
            library_service.create_book(
                isbn=book_data['isbn'],
                title=book_data['title'],
                copies_available=copies,
                author_names=book_data.get('authors', []),
                genre_names=book_data.get('categories', [])
            )
            return redirect(url_for('library_page', message='Книга успешно добавлена'))
        except library_service.BookAlreadyExists:
            return redirect(url_for('library_page', error='Книга уже существует в библиотеке'))
        except Exception as e:
            return redirect(url_for('library_page', error=str(e)))

    @app.route('/library')
    @login_required
    def library_page():
        is_admin = current_user.is_admin()
        user_name = current_user.full_name
        
        navigation = presentation_service.build_navigation(True, is_admin, user_name)
        
        all_books = library_service.get_books()
        query = request.args.get('query', '')
        status_filter = request.args.get('status', 'all')
        
        books = library_service.search_books(query, status_filter)
        stats = library_service.get_library_stats(all_books)
        
        books_table = presentation_service.build_books_table_for_library(books, is_admin)
        status_options = presentation_service.build_status_select_options(status_filter)
        
        message = presentation_service.format_message(request.args.get('message'))
        error = presentation_service.format_error(request.args.get('error'))
        
        return render_template('library.html',
                             navigation=navigation,
                             total_books=stats['total'],
                             query=query,
                             status_options=status_options,
                             result_count=len(books),
                             available_books=stats['available'],
                             books_table=books_table,
                             message=message,
                             error=error)

    @app.route('/add-book', methods=['GET', 'POST'])
    @login_required
    @admin_required
    def add_book_page():
        user_name = current_user.full_name
        navigation = presentation_service.build_navigation(True, True, user_name)
        
        query = request.args.get('query', '')
        error_text = None
        
        if request.method == 'POST' and 'isbn' in request.form:
            isbn = request.form.get('isbn')
            title = request.form.get('title')
            copies = request.form.get('copies', 1, type=int)
            authors = list(set([a.strip() for a in request.form.get('authors', '').split(',') if a.strip()]))
            genres = list(set([g.strip() for g in request.form.get('genres', '').split(',') if g.strip()]))
            
            try:
                library_service.create_book(isbn, title, copies, authors, genres)
                return redirect(url_for('library_page', message='Книга успешно добавлена'))
            except Exception as e:
                error_text = str(e)
        
        google_books_results = ''
        if query:
            try:
                books = google_books_service.search_books(query)
                google_books_results = presentation_service.build_google_books_results(books, query)
            except Exception as e:
                error_text = str(e)
        
        error = presentation_service.format_error(error_text)
        message = presentation_service.format_message(request.args.get('message'))
        
        return render_template('add_book.html',
                             navigation=navigation,
                             query=query,
                             google_books_results=google_books_results,
                             error=error,
                             message=message)

    @app.route('/issue-book')
    @login_required
    @admin_required
    def issue_book_page():
        user_name = current_user.full_name
        navigation = presentation_service.build_navigation(True, True, user_name)
        
        query = request.args.get('query', '')
        books = library_service.search_books(query=query, status_filter='available')
        
        books_table = presentation_service.build_books_table_for_admin(books, query, '/issue-book')
        
        return render_template('issue_book.html',
                             navigation=navigation,
                             query=query,
                             books_table=books_table)

    @app.route('/issue-book/<isbn>', methods=['GET', 'POST'])
    @login_required
    @admin_required
    def issue_book_confirm(isbn):
        user_name = current_user.full_name
        navigation = presentation_service.build_navigation(True, True, user_name)
        
        all_books = library_service.get_books()
        book = next((b for b in all_books if b['isbn'] == isbn), None)
        if not book:
            return redirect(url_for('issue_book_page', error='Книга не найдена'))

        user_reservations_table = ''
        error_text = None

        if request.method == 'POST':
            user_identifier = request.form.get('user_identifier')
            if user_identifier:
                user = user_service.find_user_by_identifier(user_identifier)

                if not user:
                    error_text = 'Читатель не найден'
                else:
                    try:
                        record_id = library_service.reserve_book(isbn, user.id)
                        library_service.issue_book(record_id)
                        return redirect(url_for('management_page', message=f'Книга выдана пользователю {user.full_name}'))
                    except Exception as e:
                        error_text = str(e)
                        active = library_service.get_active_borrows(user.id)
                        user_reservations = [r for r in active if r['status'] == 'reserved']
                        user_reservations_table = presentation_service.build_user_reservations_table(user_reservations)

        error = presentation_service.format_error(error_text)
        
        return render_template('issue_confirm.html',
                             navigation=navigation,
                             book_title=book['title'],
                             book_isbn=book['isbn'],
                             book_copies=book['copies'],
                             user_reservations_table=user_reservations_table,
                             error=error)

    @app.route('/issue-book-from-reservation', methods=['POST'])
    @login_required
    @admin_required
    def issue_book_from_reservation():
        record_id = request.form.get('record_id', type=int)
        
        try:
            library_service.issue_book(record_id)
            return redirect(url_for('management_page', message='Книга выдана'))
        except Exception as e:
            return redirect(url_for('management_page', error=str(e)))
    
    @app.route('/register-user-for-issue', methods=['POST'])
    @login_required
    @admin_required
    def register_user_for_issue():
        isbn = request.form.get('isbn')
        full_name = request.form.get('full_name')
        email = request.form.get('email')

        if user_service.check_user_exists(email):
            return redirect(url_for('issue_book_confirm', isbn=isbn, error='Пользователь с таким email уже существует'))

        user, temp_password = user_service.create_reader(email, full_name)

        try:
            record_id = library_service.reserve_book(isbn, user.id)
            library_service.issue_book(record_id)
            return redirect(url_for('management_page', message=f'Новый пользователь зарегистрирован. Пароль: {temp_password}. Книга выдана пользователю {user.full_name}.'))
        except Exception as e:
            return redirect(url_for('management_page', error=str(e)))

    @app.route('/reserve-book')
    @login_required
    @admin_required
    def reserve_book_page():
        user_name = current_user.full_name
        navigation = presentation_service.build_navigation(True, True, user_name)
        
        query = request.args.get('query', '')
        books = library_service.search_books(query=query, status_filter='available')
        
        books_table = presentation_service.build_books_table_for_admin(books, query, '/reserve-book')
        
        return render_template('reserve_book.html',
                             navigation=navigation,
                             query=query,
                             books_table=books_table)

    @app.route('/reserve-book/<isbn>', methods=['GET', 'POST'])
    @login_required
    @admin_required
    def reserve_book_confirm(isbn):
        user_name = current_user.full_name
        navigation = presentation_service.build_navigation(True, True, user_name)
        
        all_books = library_service.get_books()
        book = next((b for b in all_books if b['isbn'] == isbn), None)
        if not book:
            return redirect(url_for('reserve_book_page', error='Книга не найдена'))

        error_text = None

        if request.method == 'POST':
            user_identifier = request.form.get('user_identifier')
            if user_identifier:
                user = user_service.find_user_by_identifier(user_identifier)

                if not user:
                    error_text = 'Читатель не найден'
                else:
                    try:
                        library_service.reserve_book(isbn, user.id)
                        return redirect(url_for('management_page', message=f'Книга забронирована для пользователя {user.full_name}'))
                    except Exception as e:
                        error_text = str(e)

        error = presentation_service.format_error(error_text)
        
        return render_template('reserve_confirm.html',
                             navigation=navigation,
                             book_title=book['title'],
                             book_isbn=book['isbn'],
                             book_copies=book['copies'],
                             error=error)

    @app.route('/register-user-for-reserve', methods=['POST'])
    @login_required
    @admin_required
    def register_user_for_reserve():
        isbn = request.form.get('isbn')
        full_name = request.form.get('full_name')
        email = request.form.get('email')

        if user_service.check_user_exists(email):
            return redirect(url_for('reserve_book_confirm', isbn=isbn, error='Пользователь с таким email уже существует'))

        user, temp_password = user_service.create_reader(email, full_name)

        try:
            library_service.reserve_book(isbn, user.id)
            return redirect(url_for('management_page', message=f'Новый пользователь зарегистрирован. Пароль: {temp_password}. Книга забронирована для {user.full_name}.'))
        except Exception as e:
            return redirect(url_for('management_page', error=str(e)))

    @app.route('/edit-book/<isbn>')
    @login_required
    @admin_required
    def edit_book_page(isbn):
        user_name = current_user.full_name
        navigation = presentation_service.build_navigation(True, True, user_name)
        
        all_books = library_service.get_books()
        book = next((b for b in all_books if b['isbn'] == isbn), None)
        if not book:
            return redirect(url_for('management_page', error='Книга не найдена'))
        
        book_authors = ', '.join(book['authors']) if book['authors'] else ''
        book_genres = ', '.join(book['genres']) if book['genres'] else ''
        
        return render_template('edit_book.html',
                             navigation=navigation,
                             book_title=book['title'],
                             book_isbn=book['isbn'],
                             book_copies=book['copies'],
                             book_authors=book_authors,
                             book_genres=book_genres)

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
            return redirect(url_for('library_page', message='Книга успешно обновлена'))
        except Exception as e:
            return redirect(url_for('library_page', error=str(e)))

    @app.route('/delete-book', methods=['POST'])
    @login_required
    @admin_required
    def delete_book():
        isbn = request.form.get('isbn')
        try:
            library_service.delete_book(isbn)
            return redirect(url_for('library_page', message='Книга успешно удалена'))
        except Exception as e:
            return redirect(url_for('library_page', error=str(e)))

    @app.route('/mark-returned', methods=['POST'])
    @login_required
    @admin_required
    def mark_returned():
        record_id = request.form.get('record_id', type=int)
        return_date_str = request.form.get('return_date')
        
        try:
            library_service.return_book_by_record(record_id, return_date_str)
            return redirect(url_for('management_page', message='Книга отмечена как возвращенная'))
        except Exception as e:
            return redirect(url_for('management_page', error=str(e)))
    
    @app.route('/cancel-issued', methods=['POST'])
    @login_required
    @admin_required
    def cancel_issued():
        record_id = request.form.get('record_id', type=int)
        
        try:
            library_service.cancel_issued_book(record_id)
            return redirect(url_for('management_page', message='Выдача отменена, книга возвращена в фонд'))
        except Exception as e:
            return redirect(url_for('management_page', error=str(e)))

    @app.route('/reserve-book-user', methods=['POST'])
    @login_required
    def reserve_book_user():
        isbn = request.form.get('isbn')
        user_id = current_user.id

        try:
            library_service.reserve_book(isbn, user_id)
            return redirect(url_for('profile', message='Книга успешно зарезервирована'))
        except Exception as e:
            return redirect(url_for('profile', error=str(e)))

    @app.route('/cancel-reservation', methods=['POST'])
    @login_required
    @admin_required
    def cancel_reservation():
        record_id = request.form.get('record_id', type=int)

        try:
            library_service.cancel_reservation(record_id)
            return redirect(url_for('management_page', message='Резервация отменена'))
        except Exception as e:
            return redirect(url_for('management_page', error=str(e)))

    @app.route('/management')
    @login_required
    @admin_required
    def management_page():
        user_name = current_user.full_name
        navigation = presentation_service.build_navigation(True, True, user_name)
        
        status_filter = request.args.get('status', 'all')
        user_email = request.args.get('user_email', '')
        user_ticket = request.args.get('user_ticket', '')
        
        try:
            all_records = library_service.get_all_records()
            records = library_service.filter_records(all_records, status_filter, user_email, user_ticket)
        except Exception as e:
            records = []
            error_text = str(e)
        else:
            error_text = request.args.get('error')
        
        status_options = presentation_service.build_management_status_options(status_filter)
        records_table = presentation_service.build_management_records_table(records)
        
        message = presentation_service.format_message(request.args.get('message'))
        error = presentation_service.format_error(error_text)
        
        return render_template('management.html',
                             navigation=navigation,
                             user_email=user_email,
                             user_ticket=user_ticket,
                             status_options=status_options,
                             records_count=len(records),
                             records_table=records_table,
                             message=message,
                             error=error)

    # API endpoints
    @app.route('/api/v1/books', methods=['GET'])
    def get_books():
        return jsonify({'books': library_service.get_books()}), 200

    @app.route('/api/v1/books', methods=['POST'])
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
    def get_borrow_history():
        try:
            isbn = request.args.get('isbn')
            user_id = request.args.get('user_id')
            history = library_service.get_borrow_history(isbn, user_id)
            return jsonify({'history': history}), 200
        except Exception:
            return jsonify({'error': 'Server error'}), 500

    @app.route('/api/v1/active-borrows', methods=['GET'])
    def get_active_borrows():
        try:
            user_id = request.args.get('user_id')
            active_borrows = library_service.get_active_borrows(user_id)
            return jsonify({'active_borrows': active_borrows}), 200
        except Exception:
            return jsonify({'error': 'Server error'}), 500

    @app.route('/api/v1/search/google-books', methods=['GET'])
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
    def get_google_book_by_isbn(isbn):
        try:
            book = google_books_service.get_book_by_isbn(isbn)
            if not book:
                return jsonify({'error': 'Book not found'}), 404
            return jsonify(book), 200
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/v1/import/google-books', methods=['POST'])
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

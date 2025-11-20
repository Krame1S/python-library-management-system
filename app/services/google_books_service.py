import requests

GOOGLE_BOOKS_API_URL = "https://www.googleapis.com/books/v1/volumes"

def search_books(query, max_results=10):
    try:
        params = {
            'q': query,
            'maxResults': max_results,
            'langRestrict': 'ru'
        }
        response = requests.get(GOOGLE_BOOKS_API_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if 'items' not in data:
            return []
        
        books = []
        for item in data['items']:
            volume_info = item.get('volumeInfo', {})
            industry_identifiers = volume_info.get('industryIdentifiers', [])
            
            isbn_13 = None
            isbn_10 = None
            for identifier in industry_identifiers:
                if identifier.get('type') == 'ISBN_13':
                    isbn_13 = identifier.get('identifier')
                elif identifier.get('type') == 'ISBN_10':
                    isbn_10 = identifier.get('identifier')
            
            isbn = isbn_13 or isbn_10 or 'N/A'
            
            book = {
                'isbn': isbn,
                'title': volume_info.get('title', 'Без названия')[:30],
                'authors': volume_info.get('authors', []),
                'categories': volume_info.get('categories', []),
                'publisher': volume_info.get('publisher', 'Неизвестно'),
                'published_date': volume_info.get('publishedDate', 'Неизвестно'),
                'description': volume_info.get('description', 'Описание отсутствует')[:200],
                'page_count': volume_info.get('pageCount', 0),
                'language': volume_info.get('language', 'unknown'),
                'thumbnail': volume_info.get('imageLinks', {}).get('thumbnail', ''),
                'preview_link': volume_info.get('previewLink', '')
            }
            books.append(book)
        
        return books
    except requests.RequestException as e:
        raise Exception(f"Error connecting to Google Books API: {str(e)}")
    except Exception as e:
        raise Exception(f"Error processing Google Books data: {str(e)}")

def get_book_by_isbn(isbn):
    try:
        params = {'q': f'isbn:{isbn}'}
        response = requests.get(GOOGLE_BOOKS_API_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if 'items' not in data or len(data['items']) == 0:
            return None
        
        volume_info = data['items'][0].get('volumeInfo', {})
        
        return {
            'isbn': isbn,
            'title': volume_info.get('title', 'Без названия')[:30],
            'authors': volume_info.get('authors', []),
            'categories': volume_info.get('categories', []),
            'publisher': volume_info.get('publisher', 'Неизвестно'),
            'published_date': volume_info.get('publishedDate', 'Неизвестно'),
            'description': volume_info.get('description', 'Описание отсутствует'),
            'page_count': volume_info.get('pageCount', 0),
            'thumbnail': volume_info.get('imageLinks', {}).get('thumbnail', '')
        }
    except requests.RequestException as e:
        raise Exception(f"Error connecting to Google Books API: {str(e)}")
    except Exception as e:
        raise Exception(f"Error processing Google Books data: {str(e)}")
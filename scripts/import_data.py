import os
import sys
import uuid
import random
import ast
import datetime
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import NODES, get_node_index, TOTAL_AUTHORS, BOOKS_PER_AUTHOR
from nodes.models import Base, Author, Book

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV_PATH = os.path.join(PROJECT_ROOT, "Book_Details.csv", "Book_Details.csv")

UK_AUTHORS = {
    "J.K. Rowling", "Agatha Christie", "Terry Pratchett", "Neil Gaiman",
    "C.S. Lewis", "William Shakespeare", "Charles Dickens", "Jane Austen",
    "J.R.R. Tolkien", "Arthur Conan Doyle", "George Orwell", "Roald Dahl",
    "Douglas Adams", "Philip Pullman", "Ian Fleming", "Oscar Wilde",
    "Aldous Huxley", "Virginia Woolf", "Charlotte Bronte", "Emily Bronte",
    "Mary Shelley", "Thomas Hardy", "H.G. Wells", "Rudyard Kipling",
    "Terry Brooks", "Diana Wynne Jones", "Kazuo Ishiguro", "Zadie Smith",
    "Ian McEwan", "Nick Hornby", "John le Carre", "Ken Follett",
    "Salman Rushdie", "Anthony Horowitz", "Jacqueline Wilson",
    "Enid Blyton", "Beatrix Potter", "A.A. Milne", "Lewis Carroll",
    "Robert Louis Stevenson", "Bram Stoker", "Joseph Conrad",
    "E.M. Forster", "Evelyn Waugh", "Graham Greene", "P.G. Wodehouse",
    "Hilary Mantel", "Sebastian Faulks", "Julian Barnes", "Martin Amis",
}

COUNTRY_POOL = [
    ("United Kingdom", 40),
    ("United States", 30),
    ("Canada", 5),
    ("Australia", 5),
    ("India", 4),
    ("France", 3),
    ("Germany", 3),
    ("Japan", 2),
    ("Brazil", 2),
    ("Ireland", 2),
    ("South Africa", 1),
    ("Nigeria", 1),
    ("New Zealand", 1),
    ("Italy", 1),
]


def assign_country(author_name):
    if author_name in UK_AUTHORS:
        return "United Kingdom"

    countries = []
    for country, weight in COUNTRY_POOL:
        countries.extend([country] * weight)

    random.seed(hash(author_name) % 2**32)
    return random.choice(countries)


def parse_num_pages(raw):
    if pd.isna(raw):
        return None
    try:
        val = ast.literal_eval(str(raw))
        if isinstance(val, list) and len(val) > 0:
            if val[0] is None:
                return None
            return int(val[0])
        if val is None:
            return None
        return int(val)
    except (ValueError, SyntaxError, IndexError, TypeError):
        try:
            digits = ''.join(c for c in str(raw) if c.isdigit())
            return int(digits) if digits else None
        except (ValueError, IndexError):
            return None


def parse_genres(raw):
    if pd.isna(raw):
        return None
    try:
        val = ast.literal_eval(str(raw))
        if isinstance(val, list):
            return ", ".join(val[:5])
        return str(val)
    except (ValueError, SyntaxError):
        return str(raw)[:500]


def parse_publication_info(raw):
    if pd.isna(raw):
        return None
    try:
        val = ast.literal_eval(str(raw))
        if isinstance(val, list) and len(val) > 0:
            return str(val[0])
        return str(val)
    except (ValueError, SyntaxError):
        return str(raw)[:500]


def parse_int_safe(val):
    if pd.isna(val):
        return None
    try:
        return int(float(str(val).replace(",", "")))
    except (ValueError, TypeError):
        return None


def parse_float_safe(val):
    if pd.isna(val):
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def main():
    print("=" * 60)
    print("  ETL: Import Goodreads CSV -> 3 Distributed SQLite Nodes")
    print("=" * 60)

    print(f"\n[1/5] Reading CSV: {CSV_PATH}")
    df = pd.read_csv(CSV_PATH)
    print(f"  Total rows in CSV: {len(df)}")
    print(f"  Columns: {list(df.columns)}")

    print(f"\n[2/5] Selecting top {TOTAL_AUTHORS} authors by book count...")
    books_per_author = df.groupby('author').size().sort_values(ascending=False)

    ascii_authors = books_per_author[
        books_per_author.index.str.match(r'^[A-Za-z]', na=False)
    ]
    top_authors = ascii_authors.head(TOTAL_AUTHORS).index.tolist()
    print(f"  Selected {len(top_authors)} authors")
    print(f"  Book range: {ascii_authors[top_authors[-1]]} to {ascii_authors[top_authors[0]]}")

    df_filtered = df[df['author'].isin(top_authors)].copy()
    print(f"  Total book records after filtering: {len(df_filtered)}")

    print(f"\n[3/5] Building Author and Book objects with UUIDs (LOID)...")
    authors_data = {}
    books_data = []

    for author_name in top_authors:
        author_oid = str(uuid.uuid4())
        country = assign_country(author_name)
        
        # Auto-generate a realistic birth year based on hash to keep it deterministic
        random.seed(hash(author_name) % 2**32)
        birth_year = random.randint(1800, 1980)

        author_books = df_filtered[df_filtered['author'] == author_name]
        author_link = author_books.iloc[0]['authorlink'] if not author_books.empty else None

        authors_data[author_name] = {
            'oid': author_oid,
            'name': author_name,
            'country': country,
            'author_link': author_link,
            'birth_year': birth_year,
            'node_index': get_node_index(author_name),
        }

        book_rows = author_books.head(BOOKS_PER_AUTHOR)
        
        for _, row in book_rows.iterrows():
            book_oid = str(uuid.uuid4())
            books_data.append({
                'oid': book_oid,
                'author_oid': author_oid,
                'author_name': author_name,
                'title': str(row['book_title'])[:500] if pd.notna(row['book_title']) else 'Unknown',
                'average_rating': parse_float_safe(row.get('average_rating')),
                'num_ratings': parse_int_safe(row.get('num_ratings')),
                'num_reviews': parse_int_safe(row.get('num_reviews')),
                'num_pages': parse_num_pages(row.get('num_pages')),
                'genres': parse_genres(row.get('genres')),
                'publication_info': parse_publication_info(row.get('publication_info')),
                'description': str(row.get('book_details', ''))[:2000] if pd.notna(row.get('book_details')) else None,
                'cover_image_uri': str(row.get('cover_image_uri', ''))[:500] if pd.notna(row.get('cover_image_uri')) else None,
                'node_index': get_node_index(author_name),
            })

    uk_count = sum(1 for a in authors_data.values() if a['country'] == 'United Kingdom')
    us_count = sum(1 for a in authors_data.values() if a['country'] == 'United States')
    print(f"  Authors: {len(authors_data)}")
    print(f"  Books: {len(books_data)}")
    print(f"  UK authors: {uk_count} | US authors: {us_count}")

    node_counts = {}
    for a in authors_data.values():
        idx = a['node_index']
        node_counts[idx] = node_counts.get(idx, 0) + 1
    for idx, count in sorted(node_counts.items()):
        print(f"  {NODES[idx]['name']}: {count} authors")

    print(f"\n[4/5] Creating SQLite databases and inserting data...")
    for node in NODES:
        db_path = node['db_path']
        os.makedirs(os.path.dirname(db_path), exist_ok=True)

        if os.path.exists(db_path):
            os.remove(db_path)
            print(f"  Removed old: {db_path}")

        engine = create_engine(f"sqlite:///{db_path}", echo=False)
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        session = Session()

        node_idx = NODES.index(node)
        node_authors = [a for a in authors_data.values() if a['node_index'] == node_idx]
        node_books = [b for b in books_data if b['node_index'] == node_idx]

        for a in node_authors:
            author = Author(
                oid=a['oid'],
                name=a['name'],
                country=a['country'],
                author_link=a['author_link'],
                birth_year=a['birth_year'],
                created_at=datetime.datetime.utcnow(),
            )
            session.add(author)

        for b in node_books:
            book = Book(
                oid=b['oid'],
                author_oid=b['author_oid'],
                title=b['title'],
                average_rating=b['average_rating'],
                num_ratings=b['num_ratings'],
                num_reviews=b['num_reviews'],
                num_pages=b['num_pages'],
                genres=b['genres'],
                publication_info=b['publication_info'],
                description=b['description'],
                cover_image_uri=b['cover_image_uri'],
                created_at=datetime.datetime.utcnow(),
            )
            session.add(book)

        session.commit()
        session.close()
        engine.dispose()

        print(f"  {node['name']}: {len(node_authors)} authors, {len(node_books)} books -> {db_path}")

    print(f"\n[5/5] Verification...")
    for node in NODES:
        engine = create_engine(f"sqlite:///{node['db_path']}", echo=False)
        Session = sessionmaker(bind=engine)
        session = Session()
        a_count = session.query(Author).count()
        b_count = session.query(Book).count()
        uk_in_node = session.query(Author).filter(Author.country == 'United Kingdom').count()
        session.close()
        engine.dispose()
        print(f"  {node['name']}: {a_count} authors ({uk_in_node} UK), {b_count} books")

    print("\n" + "=" * 60)
    print("  ETL Complete! Data is ready for distributed queries.")
    print("=" * 60)


if __name__ == "__main__":
    main()

import datetime
from sqlalchemy import Column, Integer, String, Float, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()

class Author(Base):

    __tablename__ = 'authors'

    oid = Column(String(36), primary_key=True)
    name = Column(String(200), nullable=False, index=True)
    country = Column(String(100), nullable=False, index=True)
    author_link = Column(String(500))
    birth_year = Column(Integer)
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.UTC))

    books = relationship(
        "Book", back_populates="author",
        cascade="all, delete-orphan",
        lazy="select"
    )

    def to_dict(self, include_books=False):
        result = {
            'oid': self.oid,
            'name': self.name,
            'country': self.country,
            'author_link': self.author_link,
            'birth_year': self.birth_year,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
        if include_books:
            result['books'] = [b.to_dict() for b in self.books]
        return result


class Book(Base):

    __tablename__ = 'books'

    oid = Column(String(36), primary_key=True)
    author_oid = Column(String(36), ForeignKey('authors.oid'), nullable=False, index=True)
    title = Column(String(500), nullable=False)
    average_rating = Column(Float)
    num_ratings = Column(Integer)
    num_reviews = Column(Integer)
    num_pages = Column(Integer)
    genres = Column(String(500))
    publication_info = Column(String(500))
    description = Column(Text)
    cover_image_uri = Column(String(500))
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.UTC))

    author = relationship("Author", back_populates="books")

    def to_dict(self):
        return {
            'oid': self.oid,
            'author_oid': self.author_oid,
            'title': self.title,
            'average_rating': self.average_rating,
            'num_ratings': self.num_ratings,
            'num_reviews': self.num_reviews,
            'num_pages': self.num_pages,
            'genres': self.genres,
            'publication_info': self.publication_info,
            'description': self.description,
            'cover_image_uri': self.cover_image_uri,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

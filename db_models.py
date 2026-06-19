from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Text
from sqlalchemy import ForeignKey
from sqlalchemy import Float

from sqlalchemy.orm import relationship

from database import Base

class Brand(Base):
    __tablename__ = "brands"

    id = Column(Integer, primary_key=True)

    domain = Column(String)
    visual_blueprint = Column(Text)
    aspect_ratio = Column(String)

    pages = relationship(
        "Page",
        back_populates="brand",
        cascade="all, delete-orphan"
    )
class Page(Base):
    __tablename__ = "pages"

    id = Column(Integer, primary_key=True)

    brand_id = Column(
        Integer,
        ForeignKey("brands.id")
    )

    group_name = Column(String)
    url = Column(Text)
    anchor_text = Column(Text)

    brand = relationship(
        "Brand",
        back_populates="pages"
    )

    screenshots = relationship(
        "Screenshot",
        back_populates="page",
        cascade="all, delete-orphan"
    )

class Screenshot(Base):
    __tablename__ = "screenshots"

    id = Column(Integer, primary_key=True)

    page_id = Column(
        Integer,
        ForeignKey("pages.id")
    )

    image_path = Column(Text)
    photo_details = Column(Text)
    aspect_ratio = Column(String)

    scroll_y = Column(Integer)
    priority = Column(Float)

    page = relationship(
        "Page",
        back_populates="screenshots"
    )
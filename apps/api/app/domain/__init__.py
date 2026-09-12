"""Import every model module so Base.metadata is fully populated for create_all()."""

from app.domain import energy, intelligence, structure, system  # noqa: F401

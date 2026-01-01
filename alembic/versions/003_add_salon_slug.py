"""add salon slug

Revision ID: 003
Revises: 002
Create Date: 2025-11-19

"""
from alembic import op
import sqlalchemy as sa
import re


# revision identifiers, used by Alembic.
revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def generate_slug(name: str, existing_slugs: set) -> str:
    """Generate a unique slug from salon name"""
    base_slug = re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')
    slug = base_slug
    counter = 1
    while slug in existing_slugs:
        slug = f"{base_slug}-{counter}"
        counter += 1
    existing_slugs.add(slug)
    return slug


def upgrade() -> None:
    # Add slug column as nullable first
    op.add_column('salons', sa.Column('slug', sa.String(), nullable=True))
    
    # Populate slugs for existing salons
    connection = op.get_bind()
    salons = connection.execute(sa.text("SELECT id, name FROM salons")).fetchall()
    
    existing_slugs = set()
    for salon_id, name in salons:
        slug = generate_slug(name, existing_slugs)
        connection.execute(
            sa.text("UPDATE salons SET slug = :slug WHERE id = :id"),
            {"slug": slug, "id": salon_id}
        )
    
    # Make slug non-nullable and add unique constraint
    op.alter_column('salons', 'slug', nullable=False)
    op.create_index(op.f('ix_salons_slug'), 'salons', ['slug'], unique=True)


def downgrade() -> None:
    op.drop_index(op.f('ix_salons_slug'), table_name='salons')
    op.drop_column('salons', 'slug')

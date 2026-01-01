"""restructure services remove template pricing

Revision ID: 012
Revises: 011
Create Date: 2025-01-19

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '012'
down_revision = 'add_subscriptions_activity_logs'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    # Add new columns to services table
    services_columns = [col['name'] for col in inspector.get_columns('services')]
    
    if 'service_template_id' not in services_columns:
        op.add_column('services', sa.Column('service_template_id', sa.Integer(), nullable=True))
        op.create_foreign_key('fk_services_service_template_id', 'services', 'service_templates', ['service_template_id'], ['id'], ondelete='SET NULL')
    
    if 'is_custom' not in services_columns:
        op.add_column('services', sa.Column('is_custom', sa.Integer(), nullable=False, server_default='0'))
    
    if 'updated_at' not in services_columns:
        op.add_column('services', sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')))
    
    # Make price and duration_minutes nullable in services (salon sets them)
    op.alter_column('services', 'price',
                    existing_type=sa.DECIMAL(precision=10, scale=2),
                    nullable=True)
    op.alter_column('services', 'duration_minutes',
                    existing_type=sa.Integer(),
                    nullable=True)
    
    # Remove default_price and default_duration_minutes from service_templates
    service_templates_columns = [col['name'] for col in inspector.get_columns('service_templates')]
    
    if 'default_price' in service_templates_columns:
        op.drop_column('service_templates', 'default_price')
    
    if 'default_duration_minutes' in service_templates_columns:
        op.drop_column('service_templates', 'default_duration_minutes')
    
    # Add updated_at to service_templates if not exists
    if 'updated_at' not in service_templates_columns:
        op.add_column('service_templates', sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')))


def downgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    # Restore default_price and default_duration_minutes to service_templates
    service_templates_columns = [col['name'] for col in inspector.get_columns('service_templates')]
    
    if 'default_price' not in service_templates_columns:
        op.add_column('service_templates', sa.Column('default_price', sa.DECIMAL(precision=10, scale=2), nullable=False, server_default='0.00'))
    
    if 'default_duration_minutes' not in service_templates_columns:
        op.add_column('service_templates', sa.Column('default_duration_minutes', sa.Integer(), nullable=False, server_default='30'))
    
    if 'updated_at' in service_templates_columns:
        op.drop_column('service_templates', 'updated_at')
    
    # Make price and duration_minutes NOT NULL in services
    # First set NULL values to defaults
    op.execute("UPDATE services SET price = 0.00 WHERE price IS NULL")
    op.execute("UPDATE services SET duration_minutes = 30 WHERE duration_minutes IS NULL")
    
    op.alter_column('services', 'price',
                    existing_type=sa.DECIMAL(precision=10, scale=2),
                    nullable=False)
    op.alter_column('services', 'duration_minutes',
                    existing_type=sa.Integer(),
                    nullable=False)
    
    # Remove new columns from services table
    services_columns = [col['name'] for col in inspector.get_columns('services')]
    
    if 'updated_at' in services_columns:
        op.drop_column('services', 'updated_at')
    
    if 'is_custom' in services_columns:
        op.drop_column('services', 'is_custom')
    
    if 'service_template_id' in services_columns:
        op.drop_constraint('fk_services_service_template_id', 'services', type_='foreignkey')
        op.drop_column('services', 'service_template_id')

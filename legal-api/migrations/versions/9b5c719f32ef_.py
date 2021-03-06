"""empty message

Revision ID: 9b5c719f32ef
Revises: 94c2a694d51f
Create Date: 2019-10-25 16:03:16.370236

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9b5c719f32ef'
down_revision = '94c2a694d51f'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('filings', sa.Column('completion_date', sa.DateTime(timezone=True), nullable=True))
    op.add_column('filings', sa.Column('effective_date', sa.DateTime(timezone=True), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('filings', 'effective_date')
    op.drop_column('filings', 'completion_date')
    # ### end Alembic commands ###

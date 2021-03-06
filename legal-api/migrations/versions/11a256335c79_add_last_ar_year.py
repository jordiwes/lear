"""add_last_ar_year

Revision ID: 11a256335c79
Revises: 738437025c05
Create Date: 2021-01-21 11:02:47.150439

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '11a256335c79'
down_revision = '738437025c05'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('businesses', sa.Column('last_ar_year', sa.Integer(), nullable=True))
    op.add_column('businesses_version', sa.Column('last_ar_year', sa.Integer(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('businesses', 'last_ar_year')
    op.drop_column('businesses_version', 'last_ar_year')
    # ### end Alembic commands ###

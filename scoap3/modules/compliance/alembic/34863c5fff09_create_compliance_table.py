#
# This file is part of Invenio.
# Copyright (C) 2016-2018 CERN.
#
# Invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Create compliance table"""
import sqlalchemy_utils
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '34863c5fff09'
down_revision = 'f757abbfe351'
branch_labels = ()
depends_on = None


def upgrade():
    """Upgrade database."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('compliance',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('created', sa.DateTime(), nullable=True),
    sa.Column('updated', sa.DateTime(), nullable=True),
    sa.Column('id_record', sqlalchemy_utils.types.uuid.UUIDType(), nullable=False),
    sa.Column('results', sqlalchemy_utils.JSONType().with_variant(
            sa.dialects.postgresql.JSON(
                none_as_null=True), 'postgresql',
        ), nullable=False),
    sa.ForeignKeyConstraint(['id_record'], [u'records_metadata.id'], name=op.f('fk_compliance_id_record_records_metadata')),
    sa.PrimaryKeyConstraint('id', 'id_record', name=op.f('pk_compliance'))
    )
    # ### end Alembic commands ###


def downgrade():
    """Downgrade database."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('compliance')
    # ### end Alembic commands ###

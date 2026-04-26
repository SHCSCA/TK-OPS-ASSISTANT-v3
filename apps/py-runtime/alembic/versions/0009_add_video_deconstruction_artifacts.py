from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = '0009_add_video_deconstruction_artifacts'
down_revision = '0008_add_video_transcripts'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'video_deconstruction_artifacts',
        sa.Column('video_id', sa.String(), nullable=False),
        sa.Column('artifact_type', sa.String(), nullable=False),
        sa.Column('payload_json', sa.Text(), nullable=False),
        sa.Column('provider', sa.String(), nullable=True),
        sa.Column('model', sa.String(), nullable=True),
        sa.Column('created_at', sa.Text(), nullable=False),
        sa.Column('updated_at', sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(['video_id'], ['imported_videos.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('video_id', 'artifact_type'),
    )


def downgrade() -> None:
    op.drop_table('video_deconstruction_artifacts')

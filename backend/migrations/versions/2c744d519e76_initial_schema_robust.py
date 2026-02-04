# backend/migrations/script.py.mako
"""initial_schema_robust

Revision ID: 2c744d519e76
Revises: e7a09a09bc6d
Create Date: 2026-02-04 13:29:38.515371

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '2c744d519e76'
down_revision = 'e7a09a09bc6d'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Safely create new Enum types (idempotent)
    # This prevents "type already exists" errors if the migration partially ran before.
    op.execute("DO $$ BEGIN CREATE TYPE candidate_status_enum AS ENUM ('NEW', 'CONTACTED', 'INTERESTED', 'NOT_INTERESTED', 'NEEDS_CLARIFICATION'); EXCEPTION WHEN duplicate_object THEN null; END $$;")
    op.execute("DO $$ BEGIN CREATE TYPE job_type_enum AS ENUM ('PARSE_RESUME', 'SEND_MESSAGE', 'REPROCESS_RESUME'); EXCEPTION WHEN duplicate_object THEN null; END $$;")
    op.execute("DO $$ BEGIN CREATE TYPE job_status_enum AS ENUM ('QUEUED', 'PROCESSING', 'COMPLETED', 'FAILED'); EXCEPTION WHEN duplicate_object THEN null; END $$;")
    op.execute("DO $$ BEGIN CREATE TYPE message_status_enum AS ENUM ('PENDING', 'SENT', 'DELIVERED', 'FAILED'); EXCEPTION WHEN duplicate_object THEN null; END $$;")
    op.execute("DO $$ BEGIN CREATE TYPE reply_classification_enum AS ENUM ('INTERESTED', 'NOT_INTERESTED', 'NEEDS_CLARIFICATION', 'QUESTION'); EXCEPTION WHEN duplicate_object THEN null; END $$;")
    op.execute("DO $$ BEGIN CREATE TYPE user_role_enum AS ENUM ('RECRUITER', 'ADMIN'); EXCEPTION WHEN duplicate_object THEN null; END $$;")

    # 2. Create new tables
    op.create_table('login_attempts',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('success', sa.Boolean(), nullable=False),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_login_attempts_email'), 'login_attempts', ['email'], unique=False)
    
    op.create_table('audit_logs',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=True),
        sa.Column('action', sa.String(length=100), nullable=False),
        sa.Column('resource_type', sa.String(length=50), nullable=False),
        sa.Column('resource_id', sa.UUID(), nullable=True),
        sa.Column('details', sa.JSON(), nullable=False),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # 3. Update existing tables and columns with explicit casting
    op.alter_column('candidate_skills', 'confidence',
        existing_type=sa.DOUBLE_PRECISION(precision=53),
        nullable=False
    )
    op.alter_column('candidate_skills', 'created_at',
        existing_type=postgresql.TIMESTAMP(timezone=True),
        nullable=False,
        existing_server_default=sa.text('now()')
    )
    op.create_unique_constraint('uq_candidate_skill', 'candidate_skills', ['candidate_id', 'skill'])
    
    # Candidates Status Change
    op.alter_column('candidates', 'status',
        existing_type=postgresql.ENUM('NEW', 'CONTACTED', 'INTERESTED', 'NOT_INTERESTED', 'NEEDS_CLARIFICATION', name='candidatestatus'),
        type_=sa.Enum('NEW', 'CONTACTED', 'INTERESTED', 'NOT_INTERESTED', 'NEEDS_CLARIFICATION', name='candidate_status_enum'),
        nullable=False,
        postgresql_using='status::text::candidate_status_enum'  # <-- Added casting
    )
    
    op.alter_column('candidates', 'overall_confidence',
        existing_type=sa.DOUBLE_PRECISION(precision=53),
        nullable=False
    )
    op.alter_column('candidates', 'created_at',
        existing_type=postgresql.TIMESTAMP(timezone=True),
        nullable=False,
        existing_server_default=sa.text('now()')
    )
    op.alter_column('candidates', 'updated_at',
        existing_type=postgresql.TIMESTAMP(timezone=True),
        nullable=False
    )
    op.create_index('ix_candidate_org_owner', 'candidates', ['organization_id', 'owner_id'], unique=False)
    op.create_unique_constraint('uq_candidate_org_email', 'candidates', ['organization_id', 'email'])
    
    # Jobs Updates
    op.add_column('jobs', sa.Column('organization_id', sa.UUID(), nullable=False))
    op.add_column('jobs', sa.Column('attempts', sa.Integer(), nullable=True))
    op.add_column('jobs', sa.Column('max_attempts', sa.Integer(), nullable=True))
    op.add_column('jobs', sa.Column('locked_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('jobs', sa.Column('locked_by', sa.String(), nullable=True))
    
    op.alter_column('jobs', 'type',
        existing_type=postgresql.ENUM('PARSE_RESUME', 'SEND_MESSAGE', 'REPROCESS_RESUME', name='jobtype'),
        type_=sa.Enum('PARSE_RESUME', 'SEND_MESSAGE', 'REPROCESS_RESUME', name='job_type_enum'),
        existing_nullable=False,
        postgresql_using='type::text::job_type_enum'  # <-- Added casting
    )
    op.alter_column('jobs', 'status',
        existing_type=postgresql.ENUM('QUEUED', 'PROCESSING', 'COMPLETED', 'FAILED', name='jobstatus'),
        type_=sa.Enum('QUEUED', 'PROCESSING', 'COMPLETED', 'FAILED', name='job_status_enum'),
        nullable=False,
        postgresql_using='status::text::job_status_enum'  # <-- Added casting
    )
    
    op.create_index('ix_job_status_type', 'jobs', ['status', 'type'], unique=False)
    op.create_index(op.f('ix_jobs_organization_id'), 'jobs', ['organization_id'], unique=False)
    op.create_foreign_key(None, 'jobs', 'organizations', ['organization_id'], ['id'])
    
    # Messages Updates
    op.alter_column('messages', 'timestamp',
        existing_type=postgresql.TIMESTAMP(timezone=True),
        nullable=False,
        existing_server_default=sa.text('now()')
    )
    op.alter_column('messages', 'status',
        existing_type=postgresql.ENUM('PENDING', 'SENT', 'DELIVERED', 'FAILED', name='messagestatus'),
        type_=sa.Enum('PENDING', 'SENT', 'DELIVERED', 'FAILED', name='message_status_enum'),
        nullable=False,
        postgresql_using='status::text::message_status_enum'  # <-- Added casting
    )
    op.alter_column('messages', 'classification',
        existing_type=postgresql.ENUM('INTERESTED', 'NOT_INTERESTED', 'NEEDS_CLARIFICATION', 'QUESTION', name='replyclassification'),
        type_=sa.Enum('INTERESTED', 'NOT_INTERESTED', 'NEEDS_CLARIFICATION', 'QUESTION', name='reply_classification_enum'),
        existing_nullable=True,
        postgresql_using='classification::text::reply_classification_enum'  # <-- Added casting
    )
    op.alter_column('messages', 'requires_hr_review',
        existing_type=sa.BOOLEAN(),
        nullable=False
    )
    op.alter_column('messages', 'hr_approved',
        existing_type=sa.BOOLEAN(),
        nullable=False
    )
    
    # Organization & Parsed Fields Updates
    op.alter_column('organizations', 'created_at',
        existing_type=postgresql.TIMESTAMP(timezone=True),
        nullable=False,
        existing_server_default=sa.text('now()')
    )
    op.alter_column('parsed_fields', 'created_at',
        existing_type=postgresql.TIMESTAMP(timezone=True),
        nullable=False,
        existing_server_default=sa.text('now()')
    )
    op.alter_column('parsed_fields', 'updated_at',
        existing_type=postgresql.TIMESTAMP(timezone=True),
        nullable=False
    )
    op.create_index('ix_parsed_field_candidate_name', 'parsed_fields', ['candidate_id', 'name'], unique=False)
    
    op.alter_column('resumes', 'uploaded_at',
        existing_type=postgresql.TIMESTAMP(timezone=True),
        nullable=False,
        existing_server_default=sa.text('now()')
    )
    
    # User Updates
    op.alter_column('users', 'role',
        existing_type=postgresql.ENUM('RECRUITER', 'ADMIN', name='userrole'),
        type_=sa.Enum('RECRUITER', 'ADMIN', name='user_role_enum'),
        existing_nullable=False,
        postgresql_using='role::text::user_role_enum'  # <-- Added casting
    )
    op.alter_column('users', 'is_active',
        existing_type=sa.BOOLEAN(),
        nullable=False
    )
    op.alter_column('users', 'created_at',
        existing_type=postgresql.TIMESTAMP(timezone=True),
        nullable=False,
        existing_server_default=sa.text('now()')
    )
    op.alter_column('users', 'updated_at',
        existing_type=postgresql.TIMESTAMP(timezone=True),
        nullable=False
    )


def downgrade() -> None:
    # Basic downgrade logic as generated by Alembic
    op.alter_column('users', 'updated_at',
        existing_type=postgresql.TIMESTAMP(timezone=True),
        nullable=True)
    op.alter_column('users', 'created_at',
        existing_type=postgresql.TIMESTAMP(timezone=True),
        nullable=True,
        existing_server_default=sa.text('now()'))
    op.alter_column('users', 'is_active',
        existing_type=sa.BOOLEAN(),
        nullable=True)
    op.alter_column('users', 'role',
        existing_type=sa.Enum('RECRUITER', 'ADMIN', name='user_role_enum'),
        type_=postgresql.ENUM('RECRUITER', 'ADMIN', name='userrole'),
        existing_nullable=False,
        postgresql_using='role::text::userrole')
    op.alter_column('resumes', 'uploaded_at',
        existing_type=postgresql.TIMESTAMP(timezone=True),
        nullable=True,
        existing_server_default=sa.text('now()'))
    op.drop_index('ix_parsed_field_candidate_name', table_name='parsed_fields')
    op.alter_column('parsed_fields', 'updated_at',
        existing_type=postgresql.TIMESTAMP(timezone=True),
        nullable=True)
    op.alter_column('parsed_fields', 'created_at',
        existing_type=postgresql.TIMESTAMP(timezone=True),
        nullable=True,
        existing_server_default=sa.text('now()'))
    op.alter_column('organizations', 'created_at',
        existing_type=postgresql.TIMESTAMP(timezone=True),
        nullable=True,
        existing_server_default=sa.text('now()'))
    op.alter_column('messages', 'hr_approved',
        existing_type=sa.BOOLEAN(),
        nullable=True)
    op.alter_column('messages', 'requires_hr_review',
        existing_type=sa.BOOLEAN(),
        nullable=True)
    op.alter_column('messages', 'classification',
        existing_type=sa.Enum('INTERESTED', 'NOT_INTERESTED', 'NEEDS_CLARIFICATION', 'QUESTION', name='reply_classification_enum'),
        type_=postgresql.ENUM('INTERESTED', 'NOT_INTERESTED', 'NEEDS_CLARIFICATION', 'QUESTION', name='replyclassification'),
        existing_nullable=True,
        postgresql_using='classification::text::replyclassification')
    op.alter_column('messages', 'status',
        existing_type=sa.Enum('PENDING', 'SENT', 'DELIVERED', 'FAILED', name='message_status_enum'),
        type_=postgresql.ENUM('PENDING', 'SENT', 'DELIVERED', 'FAILED', name='messagestatus'),
        nullable=True,
        postgresql_using='status::text::messagestatus')
    op.alter_column('messages', 'timestamp',
        existing_type=postgresql.TIMESTAMP(timezone=True),
        nullable=True,
        existing_server_default=sa.text('now()'))
    op.drop_constraint(None, 'jobs', type_='foreignkey')
    op.drop_index(op.f('ix_jobs_organization_id'), table_name='jobs')
    op.drop_index('ix_job_status_type', table_name='jobs')
    op.alter_column('jobs', 'status',
        existing_type=sa.Enum('QUEUED', 'PROCESSING', 'COMPLETED', 'FAILED', name='job_status_enum'),
        type_=postgresql.ENUM('QUEUED', 'PROCESSING', 'COMPLETED', 'FAILED', name='jobstatus'),
        nullable=True,
        postgresql_using='status::text::jobstatus')
    op.alter_column('jobs', 'type',
        existing_type=sa.Enum('PARSE_RESUME', 'SEND_MESSAGE', 'REPROCESS_RESUME', name='job_type_enum'),
        type_=postgresql.ENUM('PARSE_RESUME', 'SEND_MESSAGE', 'REPROCESS_RESUME', name='jobtype'),
        existing_nullable=False,
        postgresql_using='type::text::jobtype')
    op.drop_column('jobs', 'locked_by')
    op.drop_column('jobs', 'locked_at')
    op.drop_column('jobs', 'max_attempts')
    op.drop_column('jobs', 'attempts')
    op.drop_column('jobs', 'organization_id')
    op.drop_constraint('uq_candidate_org_email', 'candidates', type_='unique')
    op.drop_index('ix_candidate_org_owner', table_name='candidates')
    op.alter_column('candidates', 'updated_at',
        existing_type=postgresql.TIMESTAMP(timezone=True),
        nullable=True)
    op.alter_column('candidates', 'created_at',
        existing_type=postgresql.TIMESTAMP(timezone=True),
        nullable=True,
        existing_server_default=sa.text('now()'))
    op.alter_column('candidates', 'overall_confidence',
        existing_type=sa.DOUBLE_PRECISION(precision=53),
        nullable=True)
    op.alter_column('candidates', 'status',
        existing_type=sa.Enum('NEW', 'CONTACTED', 'INTERESTED', 'NOT_INTERESTED', 'NEEDS_CLARIFICATION', name='candidate_status_enum'),
        type_=postgresql.ENUM('NEW', 'CONTACTED', 'INTERESTED', 'NOT_INTERESTED', 'NEEDS_CLARIFICATION', name='candidatestatus'),
        nullable=True,
        postgresql_using='status::text::candidatestatus')
    op.drop_constraint('uq_candidate_skill', 'candidate_skills', type_='unique')
    op.alter_column('candidate_skills', 'created_at',
        existing_type=postgresql.TIMESTAMP(timezone=True),
        nullable=True,
        existing_server_default=sa.text('now()'))
    op.alter_column('candidate_skills', 'confidence',
        existing_type=sa.DOUBLE_PRECISION(precision=53),
        nullable=True)
    op.drop_table('audit_logs')
    op.drop_index(op.f('ix_login_attempts_email'), table_name='login_attempts')
    op.drop_table('login_attempts')
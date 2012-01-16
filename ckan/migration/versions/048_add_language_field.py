from migrate import *

def upgrade(migrate_engine):
    migrate_engine.execute('''
BEGIN;

ALTER TABLE package
	ADD COLUMN "language" text;

ALTER TABLE package_revision
	ADD COLUMN "language" text;

UPDATE package SET language='en' where language is NULL;
UPDATE package_revision SET language='en' where language is NULL;

COMMIT;
    '''
    )

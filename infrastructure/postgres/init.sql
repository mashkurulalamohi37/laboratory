-- Runs once when the postgres volume is first created (docker-entrypoint-initdb.d).
-- Test database for the integration suite; the application database comes from POSTGRES_DB.
SELECT 'CREATE DATABASE nirnoy_test OWNER ' || current_user
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'nirnoy_test')\gexec

-- Run these commands as PostgreSQL admin to grant permissions to the DevM user
-- Connect to PostgreSQL as admin and run these commands:

-- Grant all privileges on the public schema
ALTER DEFAULT PRIVILEGES FOR USER postgres IN SCHEMA public GRANT ALL ON TABLES TO "DevM";
GRANT USAGE, CREATE ON SCHEMA public TO "DevM";
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO "DevM";
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO "DevM";

-- Alternative: Grant superuser privileges (less secure but works)
-- ALTER USER "DevM" WITH SUPERUSER;

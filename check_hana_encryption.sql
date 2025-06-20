-- HANA Database Encryption Status Check
-- Run these queries in HANA Studio, DBeaver, or hdbsql

-- =====================================================
-- 1. CHECK DATA VOLUME ENCRYPTION STATUS
-- =====================================================
SELECT 
    'DATA_VOLUME_ENCRYPTION' AS CHECK_TYPE,
    SERVICE_NAME,
    VOLUME_ID,
    ENCRYPTION_STATUS,
    ENCRYPTION_TYPE
FROM M_VOLUME_ENCRYPTION
WHERE VOLUME_TYPE = 'DATA';

-- =====================================================
-- 2. CHECK LOG VOLUME ENCRYPTION STATUS  
-- =====================================================
SELECT 
    'LOG_VOLUME_ENCRYPTION' AS CHECK_TYPE,
    SERVICE_NAME,
    VOLUME_ID,
    ENCRYPTION_STATUS,
    ENCRYPTION_TYPE
FROM M_VOLUME_ENCRYPTION
WHERE VOLUME_TYPE = 'LOG';

-- =====================================================
-- 3. CHECK ALL VOLUME ENCRYPTION STATUS
-- =====================================================
SELECT 
    'ALL_VOLUMES' AS CHECK_TYPE,
    SERVICE_NAME,
    VOLUME_TYPE,
    VOLUME_ID,
    ENCRYPTION_STATUS,
    ENCRYPTION_TYPE,
    ENCRYPTION_KEY_ID
FROM M_VOLUME_ENCRYPTION
ORDER BY SERVICE_NAME, VOLUME_TYPE, VOLUME_ID;

-- =====================================================
-- 4. CHECK BACKUP ENCRYPTION SETTINGS
-- =====================================================
SELECT 
    'BACKUP_ENCRYPTION' AS CHECK_TYPE,
    PARAMETER_NAME,
    PARAMETER_VALUE,
    DESCRIPTION
FROM M_INIFILE_CONTENTS 
WHERE SECTION_NAME = 'backup' 
AND PARAMETER_NAME LIKE '%encrypt%'
ORDER BY PARAMETER_NAME;

-- =====================================================
-- 5. CHECK SSL/TLS ENCRYPTION SETTINGS
-- =====================================================
SELECT 
    'SSL_TLS_SETTINGS' AS CHECK_TYPE,
    PARAMETER_NAME,
    PARAMETER_VALUE,
    DESCRIPTION
FROM M_INIFILE_CONTENTS 
WHERE (PARAMETER_NAME LIKE '%ssl%' OR PARAMETER_NAME LIKE '%tls%')
AND PARAMETER_VALUE IS NOT NULL
ORDER BY PARAMETER_NAME;

-- =====================================================
-- 6. CHECK COMMUNICATION ENCRYPTION
-- =====================================================
SELECT 
    'COMMUNICATION_ENCRYPTION' AS CHECK_TYPE,
    PARAMETER_NAME,
    PARAMETER_VALUE,
    DESCRIPTION
FROM M_INIFILE_CONTENTS 
WHERE SECTION_NAME = 'communication'
AND (PARAMETER_NAME LIKE '%encrypt%' OR PARAMETER_NAME LIKE '%ssl%')
ORDER BY PARAMETER_NAME;

-- =====================================================
-- 7. CHECK INTERNAL NETWORK ENCRYPTION
-- =====================================================
SELECT 
    'INTERNAL_NETWORK_ENCRYPTION' AS CHECK_TYPE,
    PARAMETER_NAME,
    PARAMETER_VALUE,
    DESCRIPTION
FROM M_INIFILE_CONTENTS 
WHERE PARAMETER_NAME IN (
    'internal_network_ssl',
    'enable_ssl',
    'ssl_enforce',
    'ssl_provider'
)
ORDER BY PARAMETER_NAME;

-- =====================================================
-- 8. CHECK COLUMN ENCRYPTION (if using column-level encryption)
-- =====================================================
SELECT 
    'COLUMN_ENCRYPTION' AS CHECK_TYPE,
    SCHEMA_NAME,
    TABLE_NAME,
    COLUMN_NAME,
    IS_ENCRYPTED
FROM TABLE_COLUMNS 
WHERE IS_ENCRYPTED = 'TRUE'
ORDER BY SCHEMA_NAME, TABLE_NAME, COLUMN_NAME;

-- =====================================================
-- 9. CHECK ENCRYPTION KEY MANAGEMENT
-- =====================================================
SELECT 
    'KEY_MANAGEMENT' AS CHECK_TYPE,
    KEY_NAME,
    KEY_TYPE,
    ALGORITHM,
    KEY_LENGTH,
    CREATED_TIME,
    LAST_USED_TIME
FROM M_ENCRYPTION_KEYS
ORDER BY KEY_NAME;

-- =====================================================
-- 10. CHECK SYSTEM ENCRYPTION OVERVIEW
-- =====================================================
SELECT 
    'ENCRYPTION_OVERVIEW' AS CHECK_TYPE,
    'Data Volume Encryption' AS FEATURE,
    CASE 
        WHEN COUNT(*) > 0 THEN 'ENABLED'
        ELSE 'DISABLED'
    END AS STATUS
FROM M_VOLUME_ENCRYPTION 
WHERE VOLUME_TYPE = 'DATA' AND ENCRYPTION_STATUS = 'ENCRYPTED'

UNION ALL

SELECT 
    'ENCRYPTION_OVERVIEW' AS CHECK_TYPE,
    'Log Volume Encryption' AS FEATURE,
    CASE 
        WHEN COUNT(*) > 0 THEN 'ENABLED'
        ELSE 'DISABLED'
    END AS STATUS
FROM M_VOLUME_ENCRYPTION 
WHERE VOLUME_TYPE = 'LOG' AND ENCRYPTION_STATUS = 'ENCRYPTED'

UNION ALL

SELECT 
    'ENCRYPTION_OVERVIEW' AS CHECK_TYPE,
    'Backup Encryption' AS FEATURE,
    CASE 
        WHEN PARAMETER_VALUE = 'true' THEN 'ENABLED'
        ELSE 'DISABLED'
    END AS STATUS
FROM M_INIFILE_CONTENTS 
WHERE PARAMETER_NAME = 'encrypt_backups'

UNION ALL

SELECT 
    'ENCRYPTION_OVERVIEW' AS CHECK_TYPE,
    'SSL/TLS Communication' AS FEATURE,
    CASE 
        WHEN PARAMETER_VALUE = 'true' THEN 'ENABLED'
        ELSE 'DISABLED'
    END AS STATUS
FROM M_INIFILE_CONTENTS 
WHERE PARAMETER_NAME = 'enable_ssl';

-- =====================================================
-- 11. CHECK SPECIFIC ENCRYPTION PARAMETERS
-- =====================================================
SELECT 
    'SPECIFIC_PARAMETERS' AS CHECK_TYPE,
    SECTION_NAME,
    PARAMETER_NAME,
    PARAMETER_VALUE,
    DESCRIPTION
FROM M_INIFILE_CONTENTS 
WHERE PARAMETER_NAME IN (
    'encrypt_backups',
    'encrypt_log_backups', 
    'enable_ssl',
    'ssl_enforce',
    'internal_network_ssl',
    'data_volume_encryption',
    'log_volume_encryption'
)
ORDER BY SECTION_NAME, PARAMETER_NAME;

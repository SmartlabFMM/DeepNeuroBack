import sqlite3
import hashlib
from datetime import datetime

class Database:
    def __init__(self, db_name='medical_ai.db'):
        self.db_name = db_name
        self.init_database()
    
    def init_database(self):
        """Initialize database and create tables"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                medical_id TEXT NOT NULL,
                user_type TEXT NOT NULL,
                email_verified INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP
            )
        ''')
        
        # Create pending verifications table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS pending_verifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                medical_id TEXT NOT NULL,
                verification_code TEXT NOT NULL,
                expiration_time TIMESTAMP NOT NULL,
                attempts INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Create password reset table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS password_resets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                verification_code TEXT NOT NULL,
                expiration_time TIMESTAMP NOT NULL,
                attempts INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create diagnosis requests table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS diagnosis_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                case_id TEXT NOT NULL,
                doctor_email TEXT NOT NULL,
                doctor_name TEXT NOT NULL,
                patient_name TEXT NOT NULL,
                patient_id TEXT NOT NULL,
                patient_age INTEGER NOT NULL,
                patient_gender TEXT NOT NULL,
                diagnosis_type TEXT NOT NULL,
                scan_date TEXT NOT NULL,
                priority TEXT NOT NULL,
                radiologist_email TEXT NOT NULL,
                description TEXT NOT NULL,
                status TEXT DEFAULT 'Pending',
                is_read INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Check and add missing columns for existing tables
        self.migrate_database(cursor)
        
        conn.commit()
        conn.close()
    
    def migrate_database(self, cursor):
        """Migrate database schema - add missing columns if they don't exist"""
        try:
            # Check if medical_id column exists
            cursor.execute("PRAGMA table_info(users)")
            columns = [column[1] for column in cursor.fetchall()]
            
            # Add medical_id column if it doesn't exist
            if 'medical_id' not in columns:
                cursor.execute('ALTER TABLE users ADD COLUMN medical_id TEXT DEFAULT "00000000"')
            
            # Add user_type column if it doesn't exist
            if 'user_type' not in columns:
                cursor.execute('ALTER TABLE users ADD COLUMN user_type TEXT DEFAULT "unknown"')

            # Add email_verified column if it doesn't exist
            if 'email_verified' not in columns:
                cursor.execute('ALTER TABLE users ADD COLUMN email_verified INTEGER DEFAULT 0')
            
            # Check diagnosis_requests table
            cursor.execute("PRAGMA table_info(diagnosis_requests)")
            diag_columns = [column[1] for column in cursor.fetchall()]
            
            # Add is_read column if it doesn't exist (for backwards compatibility)
            if 'is_read' not in diag_columns:
                cursor.execute('ALTER TABLE diagnosis_requests ADD COLUMN is_read INTEGER DEFAULT 0')
            
            # Add doctor_read and radiologist_read columns for per-user read tracking
            if 'doctor_read' not in diag_columns:
                cursor.execute('ALTER TABLE diagnosis_requests ADD COLUMN doctor_read INTEGER DEFAULT 0')
            if 'radiologist_read' not in diag_columns:
                cursor.execute('ALTER TABLE diagnosis_requests ADD COLUMN radiologist_read INTEGER DEFAULT 0')
        except sqlite3.OperationalError:
            # Table doesn't exist yet, will be created by CREATE TABLE IF NOT EXISTS
            pass
    
    def hash_password(self, password):
        """Hash password using SHA-256"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def create_user(self, name, email, password, medical_id):
        """Create a new user account"""
        try:
            # Determine user type from medical ID
            if medical_id.startswith('01'):
                user_type = 'doctor'
            elif medical_id.startswith('02'):
                user_type = 'radiologist'
            else:
                user_type = 'unknown'
            
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            
            password_hash = self.hash_password(password)
            
            cursor.execute(
                'INSERT INTO users (name, email, password_hash, medical_id, user_type) VALUES (?, ?, ?, ?, ?)',
                (name, email.lower(), password_hash, medical_id, user_type)
            )
            
            conn.commit()
            conn.close()
            return True
        except sqlite3.IntegrityError:
            # Email already exists
            return False
    
    def verify_user(self, email, password):
        """Verify user credentials"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        password_hash = self.hash_password(password)
        
        cursor.execute(
            'SELECT id FROM users WHERE email = ? AND password_hash = ?',
            (email.lower(), password_hash)
        )
        
        user = cursor.fetchone()
        
        if user:
            # Update last login
            cursor.execute(
                'UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?',
                (user[0],)
            )
            conn.commit()
        
        conn.close()
        return user is not None
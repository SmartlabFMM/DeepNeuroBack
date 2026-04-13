import sqlite3
import hashlib
import os
from datetime import datetime

class Database:
    def __init__(self, db_name='medical_ai.db'):
        self.db_name = db_name
        self.db_path = db_name
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
                doctor_email TEXT NOT NULL,
                doctor_name TEXT NOT NULL,
                patient_name TEXT NOT NULL,
                patient_id TEXT NOT NULL,
                patient_age INTEGER NOT NULL,
                patient_gender TEXT NOT NULL,
                patient_email TEXT,
                phone_number TEXT,
                diagnosis_type TEXT NOT NULL,
                scan_date TEXT NOT NULL,
                priority TEXT NOT NULL,
                radiologist_email TEXT NOT NULL,
                description TEXT NOT NULL,
                uploaded_test_file TEXT,
                segmentation_file TEXT,
                completed_at TIMESTAMP,
                status TEXT DEFAULT 'Pending',
                is_read INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Create patients table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS patients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                doctor_email TEXT NOT NULL,
                patient_name TEXT NOT NULL,
                patient_age INTEGER NOT NULL,
                patient_sex TEXT NOT NULL,
                patient_id TEXT NOT NULL,
                patient_email TEXT NOT NULL,
                phone_number TEXT NOT NULL,
                has_conditions INTEGER DEFAULT 0,
                conditions_notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(doctor_email, patient_id)
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS file_uploads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_name TEXT NOT NULL,
                file_path TEXT NOT NULL,
                file_size INTEGER DEFAULT 0,
                mime_type TEXT DEFAULT '',
                uploaded_by_email TEXT NOT NULL,
                related_entity_id TEXT DEFAULT '',
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

            # Add patient contact fields for request forms.
            if 'patient_email' not in diag_columns:
                cursor.execute('ALTER TABLE diagnosis_requests ADD COLUMN patient_email TEXT DEFAULT ""')
            if 'phone_number' not in diag_columns:
                cursor.execute('ALTER TABLE diagnosis_requests ADD COLUMN phone_number TEXT DEFAULT ""')

            # Add completion attachment fields.
            if 'uploaded_test_file' not in diag_columns:
                cursor.execute('ALTER TABLE diagnosis_requests ADD COLUMN uploaded_test_file TEXT DEFAULT ""')
            if 'segmentation_file' not in diag_columns:
                cursor.execute('ALTER TABLE diagnosis_requests ADD COLUMN segmentation_file TEXT DEFAULT ""')
            if 'completed_at' not in diag_columns:
                cursor.execute('ALTER TABLE diagnosis_requests ADD COLUMN completed_at TIMESTAMP')

            # Drop legacy case_id column by rebuilding the table if it exists.
            if 'case_id' in diag_columns:
                cursor.execute('''
                    CREATE TABLE diagnosis_requests_new (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        doctor_email TEXT NOT NULL,
                        doctor_name TEXT NOT NULL,
                        patient_name TEXT NOT NULL,
                        patient_id TEXT NOT NULL,
                        patient_age INTEGER NOT NULL,
                        patient_gender TEXT NOT NULL,
                        patient_email TEXT,
                        phone_number TEXT,
                        diagnosis_type TEXT NOT NULL,
                        scan_date TEXT NOT NULL,
                        priority TEXT NOT NULL,
                        radiologist_email TEXT NOT NULL,
                        description TEXT NOT NULL,
                        uploaded_test_file TEXT,
                        segmentation_file TEXT,
                        completed_at TIMESTAMP,
                        status TEXT DEFAULT 'Pending',
                        is_read INTEGER DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        doctor_read INTEGER DEFAULT 0,
                        radiologist_read INTEGER DEFAULT 0
                    )
                ''')
                cursor.execute('''
                    INSERT INTO diagnosis_requests_new (
                        id, doctor_email, doctor_name, patient_name, patient_id,
                        patient_age, patient_gender, patient_email, phone_number,
                        diagnosis_type, scan_date,
                        priority, radiologist_email, description, status,
                        uploaded_test_file, segmentation_file, completed_at,
                        is_read, created_at, doctor_read, radiologist_read
                    )
                    SELECT
                        id, doctor_email, doctor_name, patient_name, patient_id,
                        patient_age, patient_gender,
                        COALESCE(patient_email, ''), COALESCE(phone_number, ''),
                        diagnosis_type, scan_date,
                        priority, radiologist_email, description, status,
                        COALESCE(uploaded_test_file, ''), COALESCE(segmentation_file, ''), completed_at,
                        COALESCE(is_read, 0), created_at,
                        COALESCE(doctor_read, 0), COALESCE(radiologist_read, 0)
                    FROM diagnosis_requests
                ''')
                cursor.execute('DROP TABLE diagnosis_requests')
                cursor.execute('ALTER TABLE diagnosis_requests_new RENAME TO diagnosis_requests')

            # Check patients table
            cursor.execute("PRAGMA table_info(patients)")
            patient_columns = [column[1] for column in cursor.fetchall()]
            if 'patient_email' not in patient_columns:
                cursor.execute('ALTER TABLE patients ADD COLUMN patient_email TEXT DEFAULT ""')

            cursor.execute("PRAGMA table_info(file_uploads)")
            file_columns = [column[1] for column in cursor.fetchall()]
            if file_columns and 'related_entity_id' not in file_columns:
                cursor.execute('ALTER TABLE file_uploads ADD COLUMN related_entity_id TEXT DEFAULT ""')
        except sqlite3.OperationalError:
            # Table doesn't exist yet, will be created by CREATE TABLE IF NOT EXISTS
            pass
    
    def hash_password(self, password):
        """Hash password using SHA-256"""
        return hashlib.sha256(password.encode()).hexdigest()

    @staticmethod
    def is_valid_medical_id(medical_id):
        """Return True only for medical IDs that start with doctor/radiologist prefixes."""
        return isinstance(medical_id, str) and (medical_id.startswith('01') or medical_id.startswith('02'))
    
    def create_user(self, name, email, password, medical_id):
        """Create a new user account"""
        try:
            if not self.is_valid_medical_id(medical_id):
                return False

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


    def get_user_by_email(self, email):
        """Get user information by email"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        cursor.execute(
            'SELECT id, name, email, medical_id, user_type, created_at, last_login FROM users WHERE email = ?',
            (email.lower(),)
        )
        
        user = cursor.fetchone()
        conn.close()
        
        if user:
            return {
                'id': user[0],
                'name': user[1],
                'email': user[2],
                'medical_id': user[3],
                'user_type': user[4],
                'created_at': user[5],
                'last_login': user[6]
            }
        return None    
    
    def save_pending_verification(self, email, name, password, medical_id, verification_code, expiration_time):
        """Save pending verification data"""
        try:
            if not self.is_valid_medical_id(medical_id):
                return False

            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            
            password_hash = self.hash_password(password)
            
            # Delete any existing pending verification for this email
            cursor.execute('DELETE FROM pending_verifications WHERE email = ?', (email.lower(),))
            
            cursor.execute(
                'INSERT INTO pending_verifications (email, name, password_hash, medical_id, verification_code, expiration_time) VALUES (?, ?, ?, ?, ?, ?)',
                (email.lower(), name, password_hash, medical_id, verification_code, expiration_time)
            )
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error saving pending verification: {e}")
            return False
    
    def verify_code(self, email, verification_code):
        """Verify the provided code against pending verification"""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            
            cursor.execute(
                'SELECT id, name, password_hash, medical_id, verification_code, expiration_time FROM pending_verifications WHERE email = ?',
                (email.lower(),)
            )
            
            record = cursor.fetchone()
            
            if not record:
                conn.close()
                return False, "Verification request not found"

            # Count failed attempts for incorrect codes.
            if record[4] != verification_code:
                cursor.execute(
                    'UPDATE pending_verifications SET attempts = attempts + 1 WHERE id = ?',
                    (record[0],)
                )
                conn.commit()
                conn.close()
                return False, "Invalid verification code"
            
            # Check if code has expired
            expiration_time = datetime.fromisoformat(record[5])
            if datetime.now() > expiration_time:
                cursor.execute(
                    'UPDATE pending_verifications SET attempts = attempts + 1 WHERE id = ?',
                    (record[0],)
                )
                conn.commit()
                conn.close()
                return False, "Verification code has expired"
            
            # Create the verified user
            verification_id, name, password_hash, medical_id, _, _ = record

            if not self.is_valid_medical_id(medical_id):
                cursor.execute('DELETE FROM pending_verifications WHERE id = ?', (verification_id,))
                conn.commit()
                conn.close()
                return False, "Invalid medical ID. It must start with 01 or 02"
            
            if medical_id.startswith('01'):
                user_type = 'doctor'
            elif medical_id.startswith('02'):
                user_type = 'radiologist'
            else:
                user_type = 'unknown'
            
            cursor.execute(
                'INSERT INTO users (name, email, password_hash, medical_id, user_type, email_verified) VALUES (?, ?, ?, ?, ?, ?)',
                (name, email.lower(), password_hash, medical_id, user_type, 1)
            )
            
            # Delete pending verification
            cursor.execute('DELETE FROM pending_verifications WHERE id = ?', (verification_id,))
            
            conn.commit()
            conn.close()
            return True, "Email verified successfully"
        
        except sqlite3.IntegrityError:
            conn.close()
            return False, "Email already registered"
        except Exception as e:
            print(f"Error verifying code: {e}")
            conn.close()
            return False, "An error occurred during verification"
    
    def increment_verification_attempts(self, email):
        """Increment verification attempts for security tracking"""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            
            cursor.execute(
                'UPDATE pending_verifications SET attempts = attempts + 1 WHERE email = ?',
                (email.lower(),)
            )
            
            cursor.execute(
                'SELECT attempts FROM pending_verifications WHERE email = ?',
                (email.lower(),)
            )
            
            result = cursor.fetchone()
            conn.commit()
            conn.close()
            
            return result[0] if result else 0
        except Exception as e:
            print(f"Error incrementing attempts: {e}")
            return 0
    
    def get_pending_verification(self, email):
        """Get pending verification data"""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            
            cursor.execute(
                'SELECT email, name, verification_code, expiration_time, attempts FROM pending_verifications WHERE email = ?',
                (email.lower(),)
            )
            
            record = cursor.fetchone()
            conn.close()
            
            if record:
                return {
                    'email': record[0],
                    'name': record[1],
                    'code': record[2],
                    'expiration_time': record[3],
                    'attempts': record[4]
                }
            return None
        except Exception as e:
            print(f"Error getting pending verification: {e}")
            return None

    def save_password_reset(self, email, verification_code, expiration_time):
        """Save password reset request"""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()

            cursor.execute('DELETE FROM password_resets WHERE email = ?', (email.lower(),))

            cursor.execute(
                'INSERT INTO password_resets (email, verification_code, expiration_time) VALUES (?, ?, ?)',
                (email.lower(), verification_code, expiration_time)
            )

            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error saving password reset: {e}")
            return False

    def get_password_reset(self, email):
        """Get password reset data"""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()

            cursor.execute(
                'SELECT email, verification_code, expiration_time, attempts FROM password_resets WHERE email = ?',
                (email.lower(),)
            )

            record = cursor.fetchone()
            conn.close()

            if record:
                return {
                    'email': record[0],
                    'code': record[1],
                    'expiration_time': record[2],
                    'attempts': record[3]
                }
            return None
        except Exception as e:
            print(f"Error getting password reset: {e}")
            return None

    def increment_password_reset_attempts(self, email):
        """Increment password reset attempts for security tracking"""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()

            cursor.execute(
                'UPDATE password_resets SET attempts = attempts + 1 WHERE email = ?',
                (email.lower(),)
            )

            cursor.execute(
                'SELECT attempts FROM password_resets WHERE email = ?',
                (email.lower(),)
            )

            result = cursor.fetchone()
            conn.commit()
            conn.close()

            return result[0] if result else 0
        except Exception as e:
            print(f"Error incrementing reset attempts: {e}")
            return 0

    def verify_password_reset_code(self, email, verification_code):
        """Verify password reset code"""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()

            cursor.execute(
                'SELECT id, expiration_time FROM password_resets WHERE email = ? AND verification_code = ?',
                (email.lower(), verification_code)
            )

            record = cursor.fetchone()

            if not record:
                conn.close()
                return False, "Invalid verification code"

            expiration_time = datetime.fromisoformat(record[1])
            if datetime.now() > expiration_time:
                cursor.execute('DELETE FROM password_resets WHERE id = ?', (record[0],))
                conn.commit()
                conn.close()
                return False, "Verification code has expired"

            conn.close()
            return True, "Code verified"

        except Exception as e:
            print(f"Error verifying reset code: {e}")
            return False, "An error occurred during verification"

    def update_password(self, email, new_password):
        """Update user password"""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()

            new_hash = self.hash_password(new_password)
            cursor.execute(
                'UPDATE users SET password_hash = ? WHERE email = ?',
                (new_hash, email.lower())
            )

            cursor.execute('DELETE FROM password_resets WHERE email = ?', (email.lower(),))

            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error updating password: {e}")
            return False
        
        
    def save_diagnosis_request(self, doctor_email, doctor_name, patient_name,
                               patient_id, patient_age, patient_gender, patient_email,
                               phone_number, diagnosis_type, scan_date, priority,
                               radiologist_email, description):
        """Save a diagnosis request"""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO diagnosis_requests 
                (doctor_email, doctor_name, patient_name, patient_id, patient_age, 
                                 patient_gender, patient_email, phone_number, diagnosis_type,
                                 scan_date, priority, radiologist_email, description)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (doctor_email.lower(), doctor_name, patient_name, patient_id,
                                    patient_age, patient_gender, patient_email.lower(), phone_number,
                                    diagnosis_type, scan_date, priority, radiologist_email.lower(), description))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error saving diagnosis request: {e}")
            return False

    def save_patient(self, doctor_email, patient_name, patient_age, patient_sex,
                     patient_id, patient_email, phone_number, has_conditions=False, conditions_notes=""):
        """Save a patient profile for a doctor"""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()

            cursor.execute('''
                INSERT INTO patients
                (doctor_email, patient_name, patient_age, patient_sex, patient_id,
                 patient_email, phone_number, has_conditions, conditions_notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                doctor_email.lower(),
                patient_name,
                int(patient_age),
                patient_sex,
                patient_id,
                patient_email.lower(),
                phone_number,
                1 if has_conditions else 0,
                conditions_notes
            ))

            conn.commit()
            conn.close()
            return True, "Patient added successfully"
        except sqlite3.IntegrityError:
            return False, "Patient ID already exists for this doctor"
        except Exception as e:
            print(f"Error saving patient: {e}")
            return False, "Failed to save patient"

    def get_patients_by_doctor(self, doctor_email):
        """Get all patients added by a specific doctor"""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()

            cursor.execute('''
                  SELECT id, patient_name, patient_age, patient_sex, patient_id,
                      patient_email, phone_number, has_conditions, conditions_notes, created_at
                FROM patients
                WHERE doctor_email = ?
                ORDER BY created_at DESC
            ''', (doctor_email.lower(),))

            patients = cursor.fetchall()
            conn.close()

            return [{
                'id': p[0],
                'patient_name': p[1],
                'patient_age': p[2],
                'patient_sex': p[3],
                'patient_id': p[4],
                'patient_email': p[5],
                'phone_number': p[6],
                'has_conditions': bool(p[7]),
                'conditions_notes': p[8] or "",
                'created_at': p[9]
            } for p in patients]
        except Exception as e:
            print(f"Error retrieving patients: {e}")
            return []

    def delete_patient_by_doctor_and_id(self, doctor_email, patient_id):
        """Delete a patient profile owned by a specific doctor and patient ID."""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()

            cursor.execute(
                'DELETE FROM patients WHERE doctor_email = ? AND patient_id = ?',
                (doctor_email.lower(), patient_id)
            )

            deleted_count = cursor.rowcount
            conn.commit()
            conn.close()

            if deleted_count > 0:
                return True, "Patient deleted successfully"
            return False, "Patient not found"
        except Exception as e:
            print(f"Error deleting patient: {e}")
            return False, "Failed to delete patient"
    
    def get_requests_by_doctor(self, doctor_email):
        """Get all requests submitted by a specific doctor"""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, patient_name, patient_id, diagnosis_type,
                       radiologist_email, priority, status, created_at, doctor_read,
                       patient_age, patient_gender, patient_email, phone_number,
                       scan_date, description, uploaded_test_file, segmentation_file, completed_at
                FROM diagnosis_requests
                WHERE doctor_email = ?
                ORDER BY created_at DESC
            ''', (doctor_email.lower(),))
            
            requests = cursor.fetchall()
            conn.close()
            
            results = []
            for r in requests:
                uploaded_refs = self._split_stored_file_refs(r[15])
                uploaded_names = [self._resolve_file_reference_name(ref) for ref in uploaded_refs]
                segmentation_name = self._resolve_file_reference_name(r[16])

                results.append({
                    'id': r[0],
                    'patient_name': r[1],
                    'patient_id': r[2],
                    'diagnosis_type': r[3],
                    'radiologist_email': r[4],
                    'priority': r[5],
                    'status': r[6],
                    'created_at': r[7],
                    'is_read': r[8],  # For backwards compatibility
                    'patient_age': r[9],
                    'patient_gender': r[10],
                    'patient_email': r[11],
                    'phone_number': r[12],
                    'scan_date': r[13],
                    'description': r[14],
                    'uploaded_test_file': r[15],
                    'uploaded_test_file_names': uploaded_names,
                    'segmentation_file': r[16],
                    'segmentation_file_name': segmentation_name,
                    'completed_at': r[17],
                })

            return results
        except Exception as e:
            print(f"Error retrieving requests: {e}")
            return []
    
    def get_all_radiologists(self):
        """Get all radiologists with verified emails"""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT name, email
                FROM users
                WHERE user_type = 'radiologist' AND email_verified = 1
                ORDER BY name ASC
            ''')
            
            radiologists = cursor.fetchall()
            conn.close()
            
            return [{'name': r[0], 'email': r[1]} for r in radiologists]
        except Exception as e:
            print(f"Error retrieving radiologists: {e}")
            return []
    
    def get_requests_by_radiologist(self, radiologist_email):
        """Get all requests sent to a specific radiologist"""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, patient_name, patient_id, diagnosis_type,
                       doctor_name, doctor_email, priority, status, created_at, radiologist_read,
                       patient_age, patient_gender, patient_email, phone_number,
                       scan_date, description, uploaded_test_file, segmentation_file, completed_at
                FROM diagnosis_requests
                WHERE radiologist_email = ?
                ORDER BY created_at DESC
            ''', (radiologist_email.lower(),))
            
            requests = cursor.fetchall()
            conn.close()
            
            results = []
            for r in requests:
                uploaded_refs = self._split_stored_file_refs(r[16])
                uploaded_names = [self._resolve_file_reference_name(ref) for ref in uploaded_refs]
                segmentation_name = self._resolve_file_reference_name(r[17])

                results.append({
                    'id': r[0],
                    'patient_name': r[1],
                    'patient_id': r[2],
                    'diagnosis_type': r[3],
                    'doctor_name': r[4],
                    'doctor_email': r[5],
                    'priority': r[6],
                    'status': r[7],
                    'created_at': r[8],
                    'is_read': r[9],  # For backwards compatibility
                    'patient_age': r[10],
                    'patient_gender': r[11],
                    'patient_email': r[12],
                    'phone_number': r[13],
                    'scan_date': r[14],
                    'description': r[15],
                    'uploaded_test_file': r[16],
                    'uploaded_test_file_names': uploaded_names,
                    'segmentation_file': r[17],
                    'segmentation_file_name': segmentation_name,
                    'completed_at': r[18],
                })

            return results
        except Exception as e:
            print(f"Error retrieving requests for radiologist: {e}")
            return []

    def _split_stored_file_refs(self, stored_value):
        """Split a stored file reference string into individual references."""
        if not stored_value:
            return []
        return [item.strip() for item in str(stored_value).split('|') if item.strip()]

    def _resolve_file_reference_name(self, file_reference):
        """Resolve a file reference (ID/path) to the original display name."""
        if file_reference is None:
            return ''

        ref = str(file_reference).strip()
        if not ref:
            return ''

        if ref.isdigit():
            file_record = self.get_uploaded_file(int(ref))
            if file_record and file_record.get('file_name'):
                return str(file_record.get('file_name'))
            return ref

        return os.path.basename(ref) or ref
    
    def get_previous_cases_by_doctor(self, doctor_email):
        """Get all previous cases with patient information for autocomplete"""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT DISTINCT patient_id, patient_name, patient_age, patient_gender
                FROM diagnosis_requests
                WHERE doctor_email = ?
                ORDER BY created_at DESC
            ''', (doctor_email.lower(),))
            
            cases = cursor.fetchall()
            conn.close()
            
            return [{
                'patient_id': c[0],
                'patient_name': c[1],
                'patient_age': c[2],
                'patient_gender': c[3]
            } for c in cases]
        except Exception as e:
            print(f"Error retrieving previous cases: {e}")
            return []
    
    def mark_request_as_read(self, request_id):
        """Mark a request as read (legacy method for backwards compatibility)"""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            
            cursor.execute(
                'UPDATE diagnosis_requests SET is_read = 1 WHERE id = ?',
                (request_id,)
            )
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error marking request as read: {e}")
            return False
    
    def mark_request_as_read_by_doctor(self, request_id):
        """Mark a request as read by the doctor who sent it"""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            
            cursor.execute(
                'UPDATE diagnosis_requests SET doctor_read = 1 WHERE id = ?',
                (request_id,)
            )
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error marking request as read by doctor: {e}")
            return False
    
    def mark_request_as_read_by_radiologist(self, request_id):
        """Mark a request as read by the radiologist who received it"""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            
            cursor.execute(
                'UPDATE diagnosis_requests SET radiologist_read = 1 WHERE id = ?',
                (request_id,)
            )
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error marking request as read by radiologist: {e}")
            return False

    def complete_request_with_files(self, request_id, radiologist_email, diagnosis_type,
                                    uploaded_test_file, segmentation_file):
        """Attach uploaded files and mark request completed by radiologist."""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()

            cursor.execute(
                '''
                UPDATE diagnosis_requests
                SET diagnosis_type = ?,
                    uploaded_test_file = ?,
                    segmentation_file = ?,
                    status = 'Completed',
                    completed_at = CURRENT_TIMESTAMP,
                    doctor_read = 0
                WHERE id = ? AND radiologist_email = ?
                ''',
                (diagnosis_type, uploaded_test_file, segmentation_file, request_id, radiologist_email.lower())
            )

            updated_count = cursor.rowcount
            conn.commit()
            conn.close()

            if updated_count > 0:
                return True, "Case completed and files attached successfully"
            return False, "Request not found for this radiologist"
        except Exception as e:
            print(f"Error completing request with files: {e}")
            return False, "Failed to complete request"

    def save_uploaded_file(self, file_name, file_path, uploaded_by_email,
                           related_entity_id='', file_size=0, mime_type=''):
        """Store uploaded file metadata in SQLite."""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()

            cursor.execute(
                '''
                INSERT INTO file_uploads
                (file_name, file_path, file_size, mime_type, uploaded_by_email, related_entity_id)
                VALUES (?, ?, ?, ?, ?, ?)
                ''',
                (
                    file_name,
                    file_path,
                    int(file_size or 0),
                    mime_type or '',
                    uploaded_by_email.lower(),
                    related_entity_id or '',
                )
            )

            metadata_id = cursor.lastrowid
            conn.commit()
            conn.close()
            return metadata_id
        except Exception as e:
            print(f"Error saving uploaded file metadata: {e}")
            return None

    def get_uploaded_file(self, file_id):
        """Return a single uploaded file record by ID."""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()

            cursor.execute(
                '''
                SELECT id, file_name, file_path, file_size, mime_type,
                       uploaded_by_email, related_entity_id, created_at
                FROM file_uploads
                WHERE id = ?
                ''',
                (int(file_id),)
            )

            record = cursor.fetchone()
            conn.close()

            if not record:
                return None

            return {
                'id': record[0],
                'file_name': record[1],
                'file_path': record[2],
                'file_size': record[3],
                'mime_type': record[4],
                'uploaded_by_email': record[5],
                'related_entity_id': record[6],
                'created_at': record[7],
            }
        except Exception as e:
            print(f"Error retrieving uploaded file: {e}")
            return None

    def get_uploaded_files(self, uploaded_by_email=None, related_entity_id=None):
        """Return uploaded file metadata, optionally filtered by uploader or related entity."""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()

            query = '''
                SELECT id, file_name, file_path, file_size, mime_type,
                       uploaded_by_email, related_entity_id, created_at
                FROM file_uploads
            '''
            conditions = []
            parameters = []

            if uploaded_by_email:
                conditions.append('LOWER(uploaded_by_email) = ?')
                parameters.append(uploaded_by_email.lower())
            if related_entity_id:
                conditions.append('related_entity_id = ?')
                parameters.append(related_entity_id)

            if conditions:
                query += ' WHERE ' + ' AND '.join(conditions)

            query += ' ORDER BY created_at DESC, id DESC'

            cursor.execute(query, parameters)
            records = cursor.fetchall()
            conn.close()

            return [{
                'id': record[0],
                'file_name': record[1],
                'file_path': record[2],
                'file_size': record[3],
                'mime_type': record[4],
                'uploaded_by_email': record[5],
                'related_entity_id': record[6],
                'created_at': record[7],
            } for record in records]
        except Exception as e:
            print(f"Error retrieving uploaded files: {e}")
            return []

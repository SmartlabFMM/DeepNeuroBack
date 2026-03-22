import smtplib
import random
import string
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class EmailService:
    """Email service for sending verification codes"""
    
    def __init__(self):
        self.sender_email = os.environ.get('EMAIL_SENDER', '')
        self.app_password = os.environ.get('EMAIL_APP_PASSWORD', '')
        self.smtp_server = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = int(os.environ.get('SMTP_PORT', 587))
        
        # Validate credentials
        if not self.sender_email or not self.app_password:
            raise ValueError(
                "EMAIL_SENDER and EMAIL_APP_PASSWORD must be set in .env file"
            )
        
    def generate_verification_code(self, length=6):
        """Generate a random 6-digit verification code"""
        return ''.join(random.choices(string.digits, k=length))
    
    def send_verification_email(self, recipient_email, name, verification_code):
        """
        Send email verification code to user
        Returns True if successful, False otherwise
        """
        try:
            # Create email content
            subject = "DeepNeuro - Email Verification Code"
            
            body = f"""
            <html>
                <body style="font-family: Arial, sans-serif; background-color: #f5f5f5; margin: 0; padding: 20px;">
                    <div style="max-width: 500px; margin: 0 auto; background-color: white; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); overflow: hidden;">
                        
                        <!-- Header with gradient -->
                        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center;">
                            <h1 style="margin: 0; font-size: 28px;">🧠 DeepNeuro</h1>
                            <p style="margin: 10px 0 0 0; font-size: 14px; opacity: 0.9;">Brain Disease Diagnosis System</p>
                        </div>
                        
                        <!-- Content -->
                        <div style="padding: 30px;">
                            <h2 style="color: #333; margin-top: 0; margin-bottom: 15px;">Welcome, {name}!</h2>
                            
                            <p style="color: #666; font-size: 14px; line-height: 1.6; margin: 15px 0;">
                                Thank you for signing up with DeepNeuro. To complete your email verification, please use the code below:
                            </p>
                            
                            <!-- Verification Code Box -->
                            <div style="background-color: #fafafa; border: 2px solid #667eea; border-radius: 8px; padding: 20px; text-align: center; margin: 25px 0;">
                                <p style="color: #999; font-size: 12px; margin: 0 0 10px 0; text-transform: uppercase; letter-spacing: 2px;">Verification Code</p>
                                <p style="background: white; font-size: 32px; font-weight: bold; color: #667eea; margin: 0; padding: 15px; border-radius: 5px; letter-spacing: 5px; font-family: monospace;">
                                    {verification_code}
                                </p>
                            </div>
                            
                            <p style="color: #666; font-size: 14px; line-height: 1.6; margin: 15px 0;">
                                This code will expire in <strong>15 minutes</strong>. If you didn't request this code, please ignore this email.
                            </p>
                            
                            <p style="color: #666; font-size: 14px; line-height: 1.6; margin: 15px 0;">
                                For security reasons, never share this code with anyone, and DeepNeuro staff will never ask for it.
                            </p>
                        </div>
                        
                        <!-- Footer -->
                        <div style="background-color: #f5f5f5; border-top: 1px solid #e0e0e0; padding: 20px; text-align: center;">
                            <p style="color: #999; font-size: 12px; margin: 0;">
                                © 2026 DeepNeuro. All rights reserved.<br>
                                <a href="#" style="color: #667eea; text-decoration: none;">Privacy Policy</a> | 
                                <a href="#" style="color: #667eea; text-decoration: none;">Terms of Service</a>
                            </p>
                        </div>
                    </div>
                </body>
            </html>
            """
            
            # Create message
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = self.sender_email
            message["To"] = recipient_email
            
            # Create plain text version
            text_body = f"""
DeepNeuro - Email Verification

Welcome, {name}!

Your verification code is: {verification_code}

This code will expire in 15 minutes.

If you didn't request this code, please ignore this email.

© 2026 DeepNeuro. All rights reserved.
            """
            
            part1 = MIMEText(text_body, "plain")
            part2 = MIMEText(body, "html")
            
            message.attach(part1)
            message.attach(part2)
            
            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.sender_email, self.app_password)
                server.sendmail(self.sender_email, recipient_email, message.as_string())
            
            return True
            
        except Exception as e:
            print(f"Error sending email: {e}")
            return False

    def send_password_reset_email(self, recipient_email, name, verification_code):
        """
        Send password reset code to user
        Returns True if successful, False otherwise
        """
        try:
            subject = "DeepNeuro - Password Reset Code"

            body = f"""
            <html>
                <body style="font-family: Arial, sans-serif; background-color: #f5f5f5; margin: 0; padding: 20px;">
                    <div style="max-width: 500px; margin: 0 auto; background-color: white; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); overflow: hidden;">
                        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center;">
                            <h1 style="margin: 0; font-size: 28px;">DeepNeuro</h1>
                            <p style="margin: 10px 0 0 0; font-size: 14px; opacity: 0.9;">Brain Disease Diagnosis System</p>
                        </div>
                        <div style="padding: 30px;">
                            <h2 style="color: #333; margin-top: 0; margin-bottom: 15px;">Hello, {name}!</h2>
                            <p style="color: #666; font-size: 14px; line-height: 1.6; margin: 15px 0;">
                                We received a request to reset your password. Use the code below to continue:
                            </p>
                            <div style="background-color: #fafafa; border: 2px solid #667eea; border-radius: 8px; padding: 20px; text-align: center; margin: 25px 0;">
                                <p style="color: #999; font-size: 12px; margin: 0 0 10px 0; text-transform: uppercase; letter-spacing: 2px;">Reset Code</p>
                                <p style="background: white; font-size: 32px; font-weight: bold; color: #667eea; margin: 0; padding: 15px; border-radius: 5px; letter-spacing: 5px; font-family: monospace;">
                                    {verification_code}
                                </p>
                            </div>
                            <p style="color: #666; font-size: 14px; line-height: 1.6; margin: 15px 0;">
                                This code will expire in <strong>15 minutes</strong>. If you did not request a reset, you can ignore this email.
                            </p>
                        </div>
                        <div style="background-color: #f5f5f5; border-top: 1px solid #e0e0e0; padding: 20px; text-align: center;">
                            <p style="color: #999; font-size: 12px; margin: 0;">
                                © 2026 DeepNeuro. All rights reserved.
                            </p>
                        </div>
                    </div>
                </body>
            </html>
            """

            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = self.sender_email
            message["To"] = recipient_email

            text_body = f"""
DeepNeuro - Password Reset

Hello, {name}!

Your password reset code is: {verification_code}

This code will expire in 15 minutes.

If you did not request this reset, please ignore this email.
            """

            part1 = MIMEText(text_body, "plain")
            part2 = MIMEText(body, "html")

            message.attach(part1)
            message.attach(part2)

            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.sender_email, self.app_password)
                server.sendmail(self.sender_email, recipient_email, message.as_string())

            return True

        except Exception as e:
            print(f"Error sending reset email: {e}")
            return False

    def send_new_case_notification_email(self, recipient_email, request_info):
        """
        Send a new diagnosis request notification to the radiologist.
        Returns True if successful, False otherwise.
        """
        try:
            subject = "DeepNeuro - New Diagnosis Request Assigned"

            doctor_name = request_info.get('doctor_name', 'Unknown Doctor')
            doctor_email = request_info.get('doctor_email', 'N/A')
            patient_name = request_info.get('patient_name', 'N/A')
            patient_id = request_info.get('patient_id', 'N/A')
            patient_age = request_info.get('patient_age', 'N/A')
            patient_gender = request_info.get('patient_gender', 'N/A')
            diagnosis_type = request_info.get('diagnosis_type', 'N/A')
            priority = request_info.get('priority', 'N/A')
            description = request_info.get('description', 'N/A')

            body = f"""
            <html>
                <body style="font-family: Arial, sans-serif; background-color: #f5f5f5; margin: 0; padding: 20px;">
                    <div style="max-width: 620px; margin: 0 auto; background-color: white; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); overflow: hidden;">
                        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center;">
                            <h2 style="margin: 0; font-size: 26px;">DeepNeuro</h2>
                            <p style="margin: 10px 0 0 0; font-size: 14px; opacity: 0.9;">New diagnosis request assigned to you</p>
                        </div>

                        <div style="padding: 30px; color: #1f2937;">
                            <p style="margin-top: 0; color: #666; font-size: 14px; line-height: 1.6;">
                                You have received a new diagnosis request from Dr. <strong>{doctor_name}</strong>.
                            </p>

                            <h3 style="font-size: 15px; color: #667eea; margin: 18px 0 10px 0;">Doctor Information</h3>
                            <table style="width: 100%; border-collapse: collapse; margin-bottom: 14px;">
                                <tr>
                                    <td style="padding: 8px; border: 1px solid #e5e7eb; background: #f9fafb; font-weight: 600; width: 180px; color: #374151;">Doctor Name</td>
                                    <td style="padding: 8px; border: 1px solid #e5e7eb;">{doctor_name}</td>
                                </tr>
                                <tr>
                                    <td style="padding: 8px; border: 1px solid #e5e7eb; background: #f9fafb; font-weight: 600; color: #374151;">Doctor Email</td>
                                    <td style="padding: 8px; border: 1px solid #e5e7eb;">{doctor_email}</td>
                                </tr>
                            </table>

                            <h3 style="font-size: 15px; color: #667eea; margin: 18px 0 10px 0;">Request Information</h3>
                            <table style="width: 100%; border-collapse: collapse;">
                                <tr>
                                    <td style="padding: 8px; border: 1px solid #e5e7eb; background: #f9fafb; font-weight: 600; width: 180px; color: #374151;">Patient Name</td>
                                    <td style="padding: 8px; border: 1px solid #e5e7eb;">{patient_name}</td>
                                </tr>
                                <tr>
                                    <td style="padding: 8px; border: 1px solid #e5e7eb; background: #f9fafb; font-weight: 600; color: #374151;">Patient ID</td>
                                    <td style="padding: 8px; border: 1px solid #e5e7eb;">{patient_id}</td>
                                </tr>
                                <tr>
                                    <td style="padding: 8px; border: 1px solid #e5e7eb; background: #f9fafb; font-weight: 600; color: #374151;">Patient Age</td>
                                    <td style="padding: 8px; border: 1px solid #e5e7eb;">{patient_age}</td>
                                </tr>
                                <tr>
                                    <td style="padding: 8px; border: 1px solid #e5e7eb; background: #f9fafb; font-weight: 600; color: #374151;">Patient Gender</td>
                                    <td style="padding: 8px; border: 1px solid #e5e7eb;">{patient_gender}</td>
                                </tr>
                                <tr>
                                    <td style="padding: 8px; border: 1px solid #e5e7eb; background: #f9fafb; font-weight: 600; color: #374151;">Diagnosis Type</td>
                                    <td style="padding: 8px; border: 1px solid #e5e7eb;">{diagnosis_type}</td>
                                </tr>
                                <tr>
                                    <td style="padding: 8px; border: 1px solid #e5e7eb; background: #f9fafb; font-weight: 600; color: #374151;">Priority</td>
                                    <td style="padding: 8px; border: 1px solid #e5e7eb;">{priority}</td>
                                </tr>
                                <tr>
                                    <td style="padding: 8px; border: 1px solid #e5e7eb; background: #f9fafb; font-weight: 600; color: #374151; vertical-align: top;">Description</td>
                                    <td style="padding: 8px; border: 1px solid #e5e7eb;">{description}</td>
                                </tr>
                            </table>

                            <p style="margin: 18px 0 0 0; font-size: 13px; color: #666;">
                                Please log in to DeepNeuro to review and process this request.
                            </p>
                        </div>

                        <div style="background-color: #f5f5f5; border-top: 1px solid #e0e0e0; padding: 20px; text-align: center;">
                            <p style="color: #999; font-size: 12px; margin: 0;">
                                © 2026 DeepNeuro. All rights reserved.
                            </p>
                        </div>
                    </div>
                </body>
            </html>
            """

            text_body = f"""
DeepNeuro - New Diagnosis Request Assigned

You have received a new diagnosis request.

Doctor Information:
- Name: {doctor_name}
- Email: {doctor_email}

Request Information:
- Patient Name: {patient_name}
- Patient ID: {patient_id}
- Patient Age: {patient_age}
- Patient Gender: {patient_gender}
- Diagnosis Type: {diagnosis_type}
- Priority: {priority}
- Description: {description}

Please log in to DeepNeuro to review and process this request.
            """

            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = self.sender_email
            message["To"] = recipient_email

            part1 = MIMEText(text_body, "plain")
            part2 = MIMEText(body, "html")

            message.attach(part1)
            message.attach(part2)

            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.sender_email, self.app_password)
                server.sendmail(self.sender_email, recipient_email, message.as_string())

            return True

        except Exception as e:
            print(f"Error sending new case notification email: {e}")
            return False
    
    def get_expiration_time(self, minutes=15):
        """Get expiration time for verification code"""
        return datetime.now() + timedelta(minutes=minutes)
    
    def is_code_expired(self, expiration_time):
        """Check if verification code has expired"""
        return datetime.now() > expiration_time

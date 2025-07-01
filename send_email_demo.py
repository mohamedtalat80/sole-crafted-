#!/usr/bin/env python3
"""
MailerSend Email Demo Script

This script demonstrates how to send emails using MailerSend API.
It includes examples for:
1. Simple text email
2. HTML email
3. Template-based email
4. Email with attachments
5. Email with personalization variables

Requirements:
- pip install mailersend python-decouple
- Set MAILERSEND_API_KEY in your .env file
"""

import os
import base64
from mailersend import emails
from decouple import config
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class MailerSendDemo:
    def __init__(self):
        """Initialize MailerSend with API key"""
        self.api_key = config('MAILERSEND_API_KEY', default='')
        if not self.api_key:
            raise ValueError("MAILERSEND_API_KEY not found in environment variables")
        
        self.mailer = emails.NewEmail(self.api_key)
        self.from_email = "abnmoh525@gmail.com"
        self.from_name = "Shoe Ecommerce"

    def send_simple_text_email(self, to_email, to_name="User"):
        """Send a simple text email"""
        print("📧 Sending simple text email...")
        
        mail_body = {}
        
        # Set sender
        mail_from = {
            "name": self.from_name,
            "email": self.from_email,
        }
        
        # Set recipient
        recipients = [
            {
                "name": to_name,
                "email": to_email,
            }
        ]
        
        # Configure email
        self.mailer.set_mail_from(mail_from, mail_body)
        self.mailer.set_mail_to(recipients, mail_body)
        self.mailer.set_subject("Welcome to Shoe Ecommerce!", mail_body)
        self.mailer.set_plaintext_content(
            "Hello! Welcome to Shoe Ecommerce. We're excited to have you on board!",
            mail_body
        )
        
        # Send email
        result = self.mailer.send(mail_body)
        print(f"✅ Simple text email sent! Status: {result}")
        return result

    def send_html_email(self, to_email, to_name="User"):
        """Send an HTML email"""
        print("📧 Sending HTML email...")
        
        mail_body = {}
        
        # Set sender
        mail_from = {
            "name": self.from_name,
            "email": self.from_email,
        }
        
        # Set recipient
        recipients = [
            {
                "name": to_name,
                "email": to_email,
            }
        ]
        
        # HTML content
        html_content = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Welcome to Shoe Ecommerce</title>
        </head>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h1 style="color: #2c3e50;">👟 Welcome to Shoe Ecommerce!</h1>
                <p>Hello <strong>{to_name}</strong>,</p>
                <p>Thank you for joining Shoe Ecommerce! We're excited to have you as part of our community.</p>
                <div style="background-color: #3498db; color: white; padding: 15px; border-radius: 5px; text-align: center; margin: 20px 0;">
                    <h2>🎉 Special Welcome Offer!</h2>
                    <p>Get 10% off your first purchase with code: <strong>WELCOME10</strong></p>
                </div>
                <p>Start exploring our amazing collection of shoes today!</p>
                <p>Best regards,<br>The Shoe Ecommerce Team</p>
            </div>
        </body>
        </html>
        """.format(to_name=to_name)
        
        # Plain text fallback
        plaintext_content = f"""
        Welcome to Shoe Ecommerce!
        
        Hello {to_name},
        
        Thank you for joining Shoe Ecommerce! We're excited to have you as part of our community.
        
        Special Welcome Offer: Get 10% off your first purchase with code: WELCOME10
        
        Start exploring our amazing collection of shoes today!
        
        Best regards,
        The Shoe Ecommerce Team
        """
        
        # Configure email
        self.mailer.set_mail_from(mail_from, mail_body)
        self.mailer.set_mail_to(recipients, mail_body)
        self.mailer.set_subject("Welcome to Shoe Ecommerce! 🎉", mail_body)
        self.mailer.set_html_content(html_content, mail_body)
        self.mailer.set_plaintext_content(plaintext_content, mail_body)
        
        # Send email
        result = self.mailer.send(mail_body)
        print(f"✅ HTML email sent! Status: {result}")
        return result

    def send_template_email(self, to_email, to_name="User", template_id="your_template_id"):
        """Send a template-based email"""
        print("📧 Sending template-based email...")
        
        mail_body = {}
        
        # Set sender
        mail_from = {
            "name": self.from_name,
            "email": self.from_email,
        }
        
        # Set recipient
        recipients = [
            {
                "name": to_name,
                "email": to_email,
            }
        ]
        
        # Personalization variables
        variables = [
            {
                "email": to_email,
                "substitutions": [
                    {
                        "var": "user_name",
                        "value": to_name
                    },
                    {
                        "var": "verification_code",
                        "value": "123456"
                    },
                    {
                        "var": "company_name",
                        "value": "Shoe Ecommerce"
                    }
                ]
            }
        ]
        
        # Configure email
        self.mailer.set_mail_from(mail_from, mail_body)
        self.mailer.set_mail_to(recipients, mail_body)
        self.mailer.set_subject("Verify Your Email - {$company_name}", mail_body)
        self.mailer.set_template(template_id, mail_body)
        self.mailer.set_personalization(variables, mail_body)
        
        # Send email
        result = self.mailer.send(mail_body)
        print(f"✅ Template email sent! Status: {result}")
        return result

    def send_email_with_attachment(self, to_email, to_name="User"):
        """Send an email with attachment"""
        print("📧 Sending email with attachment...")
        
        mail_body = {}
        
        # Set sender
        mail_from = {
            "name": self.from_name,
            "email": self.from_email,
        }
        
        # Set recipient
        recipients = [
            {
                "name": to_name,
                "email": to_email,
            }
        ]
        
        # Create a simple text file as attachment
        attachment_content = "This is a sample attachment content.\nWelcome to Shoe Ecommerce!"
        attachment_encoded = base64.b64encode(attachment_content.encode()).decode()
        
        # Attachment configuration
        attachments = [
            {
                "content": attachment_encoded,
                "filename": "welcome.txt",
                "type": "text/plain"
            }
        ]
        
        # Configure email
        self.mailer.set_mail_from(mail_from, mail_body)
        self.mailer.set_mail_to(recipients, mail_body)
        self.mailer.set_subject("Welcome Package - Shoe Ecommerce", mail_body)
        self.mailer.set_html_content(
            "<h1>Welcome to Shoe Ecommerce!</h1><p>Please find your welcome package attached.</p>",
            mail_body
        )
        self.mailer.set_plaintext_content(
            "Welcome to Shoe Ecommerce!\n\nPlease find your welcome package attached.",
            mail_body
        )
        
        # Add attachments
        for attachment in attachments:
            self.mailer.add_attachment(attachment, mail_body)
        
        # Send email
        result = self.mailer.send(mail_body)
        print(f"✅ Email with attachment sent! Status: {result}")
        return result

    def send_verification_email(self, to_email, to_name="User", verification_code="123456"):
        """Send email verification code"""
        print("📧 Sending verification email...")
        
        mail_body = {}
        
        # Set sender
        mail_from = {
            "name": self.from_name,
            "email": self.from_email,
        }
        
        # Set recipient
        recipients = [
            {
                "name": to_name,
                "email": to_email,
            }
        ]
        
        # Personalization variables
        variables = [
            {
                "email": to_email,
                "substitutions": [
                    {
                        "var": "verification_code",
                        "value": verification_code
                    },
                    {
                        "var": "user_email",
                        "value": to_email
                    },
                    {
                        "var": "user_name",
                        "value": to_name
                    }
                ]
            }
        ]
        
        # HTML content
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Email Verification</title>
        </head>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h1 style="color: #2c3e50;">👟 Shoe Ecommerce</h1>
                <h2>Verify Your Email Address</h2>
                <p>Hello {to_name}!</p>
                <p>Thank you for registering with Shoe Ecommerce. To complete your registration, please verify your email address by entering the verification code below:</p>
                <div style="background-color: #3498db; color: white; padding: 15px; border-radius: 5px; text-align: center; font-size: 24px; font-weight: bold; margin: 20px 0; letter-spacing: 3px;">
                    {verification_code}
                </div>
                <p><strong>This code will expire in 10 minutes.</strong></p>
                <div style="background-color: #fff3cd; border: 1px solid #ffeaa7; color: #856404; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <strong>Important:</strong> If you didn't create an account with Shoe Ecommerce, please ignore this email.
                </div>
                <p>If you have any questions, please contact our support team.</p>
                <p>Best regards,<br>The Shoe Ecommerce Team</p>
            </div>
        </body>
        </html>
        """
        
        # Configure email
        self.mailer.set_mail_from(mail_from, mail_body)
        self.mailer.set_mail_to(recipients, mail_body)
        self.mailer.set_subject("Verify Your Email - Shoe Ecommerce", mail_body)
        self.mailer.set_html_content(html_content, mail_body)
        self.mailer.set_personalization(variables, mail_body)
        
        # Send email
        result = self.mailer.send(mail_body)
        print(f"✅ Verification email sent! Status: {result}")
        return result

    def check_api_quota(self):
        """Check MailerSend API quota"""
        print("📊 Checking API quota...")
        
        try:
            from mailersend import api_quota
            quota_checker = api_quota.NewApiQuota(self.api_key)
            quota_info = quota_checker.get_quota()
            print(f"✅ API Quota: {quota_info}")
            return quota_info
        except Exception as e:
            print(f"❌ Error checking quota: {e}")
            return None

def main():
    """Main function to demonstrate email sending"""
    print("🚀 MailerSend Email Demo")
    print("=" * 50)
    
    try:
        # Initialize MailerSend demo
        demo = MailerSendDemo()
        
        # Get recipient email from user input
        recipient_email = input("Enter recipient email address: ").strip()
        recipient_name = input("Enter recipient name (or press Enter for default): ").strip() or "User"
        
        if not recipient_email:
            print("❌ Email address is required!")
            return
        
        print(f"\n📧 Sending emails to: {recipient_email}")
        print("=" * 50)
        
        # Check API quota first
        demo.check_api_quota()
        print()
        
        # Send different types of emails
        print("1️⃣ Simple Text Email")
        demo.send_simple_text_email(recipient_email, recipient_name)
        print()
        
        print("2️⃣ HTML Email")
        demo.send_html_email(recipient_email, recipient_name)
        print()
        
        print("3️⃣ Verification Email")
        demo.send_verification_email(recipient_email, recipient_name, "123456")
        print()
        
        print("4️⃣ Email with Attachment")
        demo.send_email_with_attachment(recipient_email, recipient_name)
        print()
        
        # Template email (commented out as it requires a template ID)
        # print("5️⃣ Template Email")
        # template_id = input("Enter template ID (or press Enter to skip): ").strip()
        # if template_id:
        #     demo.send_template_email(recipient_email, recipient_name, template_id)
        # print()
        
        print("✅ All emails sent successfully!")
        print("\n📝 Note: Check your MailerSend dashboard to see the email delivery status.")
        
    except ValueError as e:
        print(f"❌ Configuration Error: {e}")
        print("Please make sure MAILERSEND_API_KEY is set in your .env file")
    except Exception as e:
        print(f"❌ Error: {e}")
        print("Please check your MailerSend API key and internet connection")

if __name__ == "__main__":
    main() 
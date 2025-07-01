#!/usr/bin/env python3
"""
Simple Django SMTP Email Sender

A simple script to send emails using Django's SMTP backend with Gmail.
Perfect for testing and basic email sending needs.

Usage:
    python simple_email_sender.py
"""

import os
import sys
import django
from decouple import config
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'shoe_ecommerce.settings')
django.setup()

from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags

def send_email(to_email, subject="Test Email", message="This is a test email"):
    """
    Send a simple email using Django SMTP
    
    Args:
        to_email (str): Recipient email address
        subject (str): Email subject
        message (str): Email message content
    """
    
    # Get email configuration from environment
    email_host_user = config('EMAIL_HOST_USER', default='abnmoh525@gmail.com')
    email_host_password = config('EMAIL_HOST_PASSWORD', default='')
    
    if not email_host_password:
        print("❌ Error: EMAIL_HOST_PASSWORD not found in environment variables")
        print("Please add your Gmail app password to your .env file")
        return False
    
    try:
        # Create HTML message
        html_message = f"""
        <html>
        <body>
            <h2>{subject}</h2>
            <p>{message}</p>
            <hr>
            <p><em>Sent from Shoe Ecommerce</em></p>
        </body>
        </html>
        """
        
        # Send email
        print(f"📧 Sending email to {to_email}...")
        result = send_mail(
            subject=subject,
            message=message,
            from_email=email_host_user,
            recipient_list=[to_email],
            html_message=html_message,
            fail_silently=False,
        )
        
        print(f"✅ Email sent successfully!")
        print(f"📊 Result: {result}")
        return True
        
    except Exception as e:
        error_message = str(e)
        print(f"❌ Error sending email: {error_message}")
        
        # Handle specific Gmail SMTP errors
        if "Authentication" in error_message:
            print("\n🔧 Gmail Authentication Error:")
            print("   - Check your EMAIL_HOST_PASSWORD in .env file")
            print("   - Make sure you're using an App Password, not your regular password")
            print("   - Enable 2-factor authentication on your Gmail account")
            print("   - Generate an App Password: Google Account → Security → App Passwords")
        
        elif "SMTP" in error_message:
            print("\n🔧 SMTP Connection Error:")
            print("   - Check your internet connection")
            print("   - Verify EMAIL_HOST_USER is correct")
            print("   - Make sure Gmail SMTP is enabled")
        
        return False

def check_gmail_setup():
    """Check Gmail SMTP setup and provide guidance"""
    print("🔍 Checking Gmail SMTP Setup...")
    print("=" * 50)
    
    email_host_user = config('EMAIL_HOST_USER', default='abnmoh525@gmail.com')
    email_host_password = config('EMAIL_HOST_PASSWORD', default='')
    
    print(f"✅ Email Host User: {email_host_user}")
    
    if not email_host_password:
        print("❌ EMAIL_HOST_PASSWORD not found")
        print("   Please add your Gmail app password to .env file")
        return False
    
    print("✅ App Password found")
    print("\n📋 Setup Checklist:")
    print("   1. ✅ Email host user configured")
    print("   2. ✅ App password configured")
    print("   3. ⏳ 2-factor authentication enabled")
    print("   4. ⏳ App password generated")
    
    print("\n🔧 Next Steps:")
    print("   1. Enable 2-factor authentication on your Gmail account")
    print("   2. Go to Google Account → Security → App Passwords")
    print("   3. Generate an app password for 'Mail'")
    print("   4. Add the password to your .env file as EMAIL_HOST_PASSWORD")
    
    return True

def main():
    """Main function"""
    print("📧 Simple Django SMTP Email Sender")
    print("=" * 40)
    
    # Check setup first
    if not check_gmail_setup():
        return
    
    print("\n" + "=" * 40)
    
    # Get email details from user
    to_email = input("Enter recipient email: ").strip()
    subject = input("Enter email subject (or press Enter for default): ").strip() or "Hello from Shoe Ecommerce!"
    message = input("Enter email message (or press Enter for default): ").strip() or "This is a test email from Shoe Ecommerce using Django SMTP!"
    
    if not to_email:
        print("❌ Recipient email is required!")
        return
    
    # Send the email
    success = send_email(to_email, subject, message)
    
    if success:
        print("\n🎉 Email sent successfully!")
        print("📝 Check the recipient's inbox for the email.")
    else:
        print("\n❌ Failed to send email.")
        print("\n🔧 Troubleshooting:")
        print("   1. Check your .env file has EMAIL_HOST_PASSWORD")
        print("   2. Make sure you're using an App Password, not regular password")
        print("   3. Enable 2-factor authentication on Gmail")
        print("   4. Check your internet connection")

if __name__ == "__main__":
    main() 
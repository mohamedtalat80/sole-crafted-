from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.utils.html import strip_tags
import os
from decouple import config
import logging

# Set up logger
logger = logging.getLogger(__name__)

class EmailService:
    def __init__(self):
        self.from_email = config('EMAIL_HOST_USER', default='abnmoh525@gmail.com')
        self.from_name = 'Shoe Ecommerce'
        logger.info(f"EmailService initialized with from_email: {self.from_email}")

    def send_verification_email(self, user_email, verification_code):
        """Send email verification code using Django SMTP with HTML template"""
        logger.info(f"=== EmailService.send_verification_email() called ===")
        logger.info(f"Parameters: user_email={user_email}, verification_code={verification_code}")
        
        subject = "Verify Your Email - Sole Crafted"
        logger.info(f"Email subject: {subject}")
        
        # Context for the template
        context = {
            'verification_code': verification_code,
            'user_email': user_email,
            'from_name': self.from_name
        }
        logger.info(f"Template context: {context}")
        
        try:
            # Render HTML content from template
            logger.info("Attempting to render HTML template...")
            html_message = render_to_string('email_templates/verification_email.html', context)
            logger.info(f"HTML template rendered successfully. Length: {len(html_message)} characters")
            
            # Create plain text version
            plain_message = f"""
            Hello!
            
            Thank you for registering with Sole Crafted. To complete your registration, please verify your email address by entering the verification code below:
            
            Verification Code: {verification_code}
            
            This code will expire in 10 minutes.
            
            Important: If you didn't create an account with Sole Crafted
            If you have any questions or need assistance, please don't hesitate to contact our support team.
            
            Best regards,
            The Shoe Ecommerce Team
            
            This email was sent to {user_email}
            """
            logger.info(f"Plain text message created. Length: {len(plain_message)} characters")
            
            # Log email configuration
            logger.info("=== Email Configuration ===")
            logger.info(f"EMAIL_BACKEND: {getattr(settings, 'EMAIL_BACKEND', 'Not set')}")
            logger.info(f"EMAIL_HOST: {getattr(settings, 'EMAIL_HOST', 'Not set')}")
            logger.info(f"EMAIL_PORT: {getattr(settings, 'EMAIL_PORT', 'Not set')}")
            logger.info(f"EMAIL_USE_TLS: {getattr(settings, 'EMAIL_USE_TLS', 'Not set')}")
            logger.info(f"EMAIL_HOST_USER: {getattr(settings, 'EMAIL_HOST_USER', 'Not set')}")
            logger.info(f"DEFAULT_FROM_EMAIL: {getattr(settings, 'DEFAULT_FROM_EMAIL', 'Not set')}")
            
            # Check if EMAIL_HOST_PASSWORD is set
            email_password = config('EMAIL_HOST_PASSWORD', default='')
            if email_password:
                logger.info("EMAIL_HOST_PASSWORD: [SET] (length: %d)", len(email_password))
            else:
                logger.error("EMAIL_HOST_PASSWORD: [NOT SET]")
            
            logger.info("=== Attempting to send email ===")
            logger.info(f"From: {self.from_email}")
            logger.info(f"To: {user_email}")
            logger.info(f"Subject: {subject}")
            
            result = send_mail(
                subject=subject,
                message=plain_message,
                from_email=self.from_email,
                recipient_list=[user_email],
                html_message=html_message,
                fail_silently=False,
            )
            
            logger.info(f"=== Email sent successfully ===")
            logger.info(f"send_mail() returned: {result}")
            return True
            
        except Exception as e:
            logger.error(f"=== Error in send_verification_email() ===")
            logger.error(f"Exception type: {type(e).__name__}")
            logger.error(f"Exception message: {str(e)}")
            logger.error(f"Exception details: {e}")
            
            # Log additional debugging information
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            
            # Re-raise the exception for the view to handle
            raise e

    def send_password_reset_email(self, user_email, otp_code):
        """Send password reset OTP using Django SMTP with HTML template"""
        logger.info(f"=== EmailService.send_password_reset_email() called ===")
        logger.info(f"Parameters: user_email={user_email}, otp_code={otp_code}")
        
        subject = "Password Reset - Shoe Ecommerce"
        logger.info(f"Email subject: {subject}")
        
        # Context for the template
        context = {
            'otp_code': otp_code,
            'user_email': user_email,
            'from_name': self.from_name
        }
        logger.info(f"Template context: {context}")
        
        try:
            # Render HTML content from template
            logger.info("Attempting to render HTML template...")
            html_message = render_to_string('email_templates/password_reset_email.html', context)
            logger.info(f"HTML template rendered successfully. Length: {len(html_message)} characters")
            
            # Create plain text version
            plain_message = f"""
            Hello!
            
            You have requested to reset your password for your Shoe Ecommerce account. Please use the OTP code below to reset your password:
            
            OTP Code: {otp_code}
            
            This code will expire in 10 minutes.
            
            If you didn't request a password reset, please ignore this email and your password will remain unchanged.
            
            If you have any questions or need assistance, please don't hesitate to contact our support team.
            
            Best regards,
            The Shoe Ecommerce Team
            
            This email was sent to {user_email}
            """
            logger.info(f"Plain text message created. Length: {len(plain_message)} characters")
            
            logger.info("=== Attempting to send email ===")
            logger.info(f"From: {self.from_email}")
            logger.info(f"To: {user_email}")
            logger.info(f"Subject: {subject}")
            
            result = send_mail(
                subject=subject,
                message=plain_message,
                from_email=self.from_email,
                recipient_list=[user_email],
                html_message=html_message,
                fail_silently=False,
            )
            
            logger.info(f"=== Email sent successfully ===")
            logger.info(f"send_mail() returned: {result}")
            return True
            
        except Exception as e:
            logger.error(f"=== Error in send_password_reset_email() ===")
            logger.error(f"Exception type: {type(e).__name__}")
            logger.error(f"Exception message: {str(e)}")
            logger.error(f"Exception details: {e}")
            
            # Log additional debugging information
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            
            # Re-raise the exception for the view to handle
            raise e 
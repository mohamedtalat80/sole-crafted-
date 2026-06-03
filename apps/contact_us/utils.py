import logging
from django.conf import settings
from apps.core.email import send_email

logger = logging.getLogger(__name__)

def send_contact_email(contact_message):
    """
    Constructs and sends an HTML email for a new contact message.
    """
    try:
        # Field name is full_name in the model
        full_name = contact_message.full_name
        email_from = contact_message.email
        subject = contact_message.subject
        message_body = contact_message.message
        
        # Construct image URL and HTML snippet
        image_url = ""
        image_html_snippet = ""
        if contact_message.image:
            # Determine if we need to prefix with SITE_URL
            raw_url = contact_message.image.url
            if raw_url.startswith('http'):
                image_url = raw_url
            else:
                # Remove trailing slash from SITE_URL if it exists, and leading slash from raw_url
                base_url = settings.SITE_URL.rstrip('/')
                image_url = f"{base_url}{raw_url}"
            
            image_html_snippet = (
                f'<p><strong>Image:</strong></p>'
                f'<p><img src="{image_url}" alt="Contact Image" style="max-width: 600px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);"></p>'
            )

        # Construct HTML body
        email_html = f"""
        <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; color: #1a1a1a; background-color: #f9f9f9; border: 1px solid #eee; border-radius: 12px;">
            <h2 style="color: #007bff; margin-bottom: 20px; border-bottom: 2px solid #007bff; padding-bottom: 10px;">New Contact Message</h2>
            <div style="margin-bottom: 15px;">
                <p style="margin: 5px 0;"><strong>From:</strong> {full_name} (<a href="mailto:{email_from}" style="color: #007bff; text-decoration: none;">{email_from}</a>)</p>
                <p style="margin: 5px 0;"><strong>Subject:</strong> {subject}</p>
            </div>
            <div style="background-color: #ffffff; padding: 15px; border-radius: 8px; border: 1px solid #e0e0e0; margin-bottom: 20px;">
                <p style="font-weight: bold; margin-top: 0; color: #555;">Message:</p>
                <p style="white-space: pre-wrap; margin-bottom: 0;">{message_body}</p>
            </div>
            {image_html_snippet}
            <div style="margin-top: 30px; padding-top: 15px; border-top: 1px solid #eee; font-size: 12px; color: #888; text-align: center;">
                <p>This message was sent from the Omarina Contact Us form.</p>
            </div>
        </div>
        """
        
        # Construct plain-text fallback
        email_text = f"New message from {full_name} ({email_from}):\n\nSubject: {subject}\n\nMessage:\n{message_body}"
        if image_url:
            email_text += f"\n\nImage URL: {image_url}"

        send_email(
            to=getattr(settings, 'INFO_EMAIL', settings.DEFAULT_FROM_EMAIL),
            subject=f"Contact Us: {subject}",
            text=email_text,
            html=email_html
        )
    except Exception as e:
        logger.error(f"Failed to send contact email: {e}")

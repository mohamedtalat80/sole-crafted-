import logging
import sib_api_v3_sdk
from django.conf import settings
from django.core.mail import send_mail as django_send_mail
from sib_api_v3_sdk.rest import ApiException

logger = logging.getLogger(__name__)


def send_email(*, to: str, subject: str, text: str = None, html: str = None) -> None:
    """
    Send a transactional email via Brevo API or standard Django SMTP.
    Controlled by settings.USE_BREVO_API.
    """
    if not to or not to.strip():
        raise ValueError("Email 'to' address cannot be empty.")
    if not text and not html:
        raise ValueError("Either 'text' or 'html' must be provided.")

    use_console = getattr(settings, "USE_CONSOLE_EMAIL", True)
    if use_console:
        print(f"\n--- EMAIL CONSOLE MODE ---")
        print(f"To: {to}")
        print(f"Subject: {subject}")
        print(f"Body: {text}")
        print(f"--------------------------\n")
        logger.info("Email simulated via console mode (USE_CONSOLE_EMAIL=True).")
        return

    use_api = getattr(settings, "USE_BREVO_API", False)
    
    if use_api:
        _send_via_brevo_api(to=to, subject=subject, text=text, html=html)
    else:
        _send_via_smtp(to=to, subject=subject, text=text, html=html)


def _send_via_brevo_api(*, to: str, subject: str, text: str, html: str) -> None:
    logger.info("Attempting to send email to %s via Brevo API...", to)
    
    configuration = sib_api_v3_sdk.Configuration()
    configuration.api_key["api-key"] = settings.BREVO_API_KEY

    api_client = sib_api_v3_sdk.ApiClient(configuration)
    api_instance = sib_api_v3_sdk.TransactionalEmailsApi(api_client)

    email = sib_api_v3_sdk.SendSmtpEmail(
        sender={"name": "Orangebay", "email": settings.DEFAULT_FROM_EMAIL},
        to=[{"email": to}],
        subject=subject,
        text_content=text,
        html_content=html,
    )

    try:
        response = api_instance.send_transac_email(email)
        logger.info("Email sent successfully via Brevo API. Message ID: %s", getattr(response, 'message_id', 'unknown'))
    except ApiException as exc:
        logger.exception("Brevo API error sending to %s: %s", to, exc)
        raise


def _send_via_smtp(*, to: str, subject: str, text: str, html: str) -> None:
    logger.info("Attempting to send email to %s via SMTP...", to)
    try:
        django_send_mail(
            subject=subject,
            message=text,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[to],
            html_message=html,
            fail_silently=False,
        )
        logger.info("Email sent successfully via SMTP.")
    except Exception as exc:
        logger.exception("SMTP error sending to %s: %s", to, exc)
        raise

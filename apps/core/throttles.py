"""
Custom throttle classes.

All classes share _EnvelopeThrottleMixin, which overrides throttle_failure() to raise
Throttled with a message that includes the exact wait time. custom_exception_handler
in apps.core.exceptions surfaces that message directly as the top-level "message" field:
  {"status": false, "message": "Rate limit exceeded. Try again in X seconds.", "errors": {}}

Class hierarchy
---------------
_EnvelopeThrottleMixin          — injects wait time into Throttled detail
  └─ _ScopedAnonThrottle        — IP-keyed (AnonRateThrottle base); set `scope` on subclass
       ├─ SocialLoginThrottle   scope="social_login"   10/min
       ├─ LoginThrottle         scope="login"           10/min
       ├─ SignUpThrottle        scope="signup"          10/min
       ├─ StrictSearchThrottle  scope="strict_search"   20/min
       └─ PasswordResetThrottle scope="password_reset"   5/hour
  └─ UserRateThrottle           — user-ID-keyed (UserRateThrottle base); scope="user"
                                  1000/day global limit for authenticated requests
"""
from rest_framework.exceptions import Throttled
from rest_framework.throttling import AnonRateThrottle
from rest_framework.throttling import UserRateThrottle as _DRFUserRateThrottle
from django.conf import settings
import math

class _EnvelopeThrottleMixin:
    def allow_request(self, request, view) -> bool:
        if settings.THROTTLE_ENABLED is False:
            return True 
        return super().allow_request(request, view)
    def throttle_failure(self):
        wait = self.wait()
        seconds = math.ceil(wait) if wait is not None else 60
        raise Throttled(
            wait=wait,
            detail=f"Rate limit exceeded. Try again in {seconds} seconds.",
        )
    
class _ScopedAnonThrottle(_EnvelopeThrottleMixin, AnonRateThrottle):
    """IP-keyed throttle for AllowAny endpoints. Subclasses must set `scope`."""
   
class UserRateThrottle(_EnvelopeThrottleMixin, _DRFUserRateThrottle):
    """Global 1000/day cap for all authenticated users. Added to DEFAULT_THROTTLE_CLASSES."""
    scope = "user"

class SocialLoginThrottle(_ScopedAnonThrottle):
    scope = "social_login"
class LoginThrottle(_ScopedAnonThrottle):
    scope = "login" 
class SignUpThrottle(_ScopedAnonThrottle):
    scope = "signup"    
class PasswordResetThrottle(_ScopedAnonThrottle):
    scope = "password_reset"
class SendVerificationEmailThrottle(_ScopedAnonThrottle):
    scope = "send_verification_email"
class SetNewPasswordThrottle(_ScopedAnonThrottle):
    scope = "set_new_password"

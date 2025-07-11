# Changelog

## [Unreleased]

### Changed
- **Fixed token validation in authenticated views**:
  - Updated `VerifyOTPView` and `ResetPasswordView` to use `request.user` from JWT token
  - Removed manual user lookup by email in authenticated views
  - Updated `PasswordResetSerializer` to remove email field (user comes from token)
  - Added proper error handling and logging for token-based operations
  - Improved security by relying on Django's automatic token validation
- **Enhanced JWT configuration and security**:
  - Added comprehensive JWT settings in `settings.py`:
    - `ACCESS_TOKEN_LIFETIME`: 5 minutes (short-lived for security)
    - `REFRESH_TOKEN_LIFETIME`: 7 days (long-lived for convenience)
    - `ROTATE_REFRESH_TOKENS`: True (new refresh token on each refresh)
    - `BLACKLIST_AFTER_ROTATION`: True (blacklist old refresh tokens)
    - `UPDATE_LAST_LOGIN`: True (track user activity)
  - Added `rest_framework_simplejwt.token_blacklist` to `INSTALLED_APPS`
  - Configured proper token security with blacklisting support
- **Added comprehensive Swagger/DRF-YASG API documentation**:
  - Added Swagger URLs to main URL configuration
  - Added detailed API documentation with `@swagger_auto_schema` decorators
  - Organized APIs into tags: "Authentication" and "Password Reset"
  - Added request/response examples for all endpoints
  - Added operation descriptions and summaries
  - Configured Swagger UI and ReDoc interfaces
  - Added proper OpenAPI schema definitions
- **Fixed template directory structure for email templates**:
  - Moved `email_templates/` directory inside `templates/` directory
  - Updated Django settings to point to correct template directory
  - Fixed `TemplateDoesNotExist` error for email templates
- **Added comprehensive logging for email debugging**:
  - Added detailed logging to `RegisterView` to track email sending process
  - Enhanced `EmailService` with step-by-step logging for email operations
  - Added logging configuration to Django settings for better debugging
  - Logs include email configuration, template rendering, and SMTP operations
  - Added debug information to API responses when email fails
  - Logs are saved to both console and `debug.log` file
- **Updated email templates to use proper Django template syntax**:
  - Fixed `email_templates/verification_email.html` to use `{{ verification_code }}` instead of `{$verification_code}`
  - Fixed `email_templates/password_reset_email.html` to use `{{ otp_code }}` instead of `{$otp_code}`
  - Updated `users/services.py` to properly render HTML templates with context
  - Added `email_templates` directory to Django template directories in `settings.py`
  - Enhanced email service to provide both HTML and plain text versions
  - Improved email content with better formatting and security notes
- **Switched from MailerSend to Django SMTP backend**:
  - Replaced MailerSend API with Django's built-in SMTP backend
  - Updated email configuration in `settings.py` to use Gmail SMTP
  - Replaced `MailerSendService` with `EmailService` in `users/services.py`
  - Updated `users/views.py` to use new `EmailService`
  - Removed MailerSend-specific error handling
  - Updated `simple_email_sender.py` to use Django SMTP
  - Removed `mailersend` dependency from `requirements.txt`
  - Email configuration now uses:
    - `EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'`
    - `EMAIL_HOST = 'smtp.gmail.com'`
    - `EMAIL_PORT = 587`
    - `EMAIL_USE_TLS = True`
    - `EMAIL_HOST_USER = 'abnmoh525@gmail.com'`
    - `EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD')'`
    - `DEFAULT_FROM_EMAIL = 'abnmoh525@gmail.com'`
- Refactored `users/views.py` to implement new authentication system with:
  - Email verification functionality
  - Password reset with OTP
  - JWT token-based authentication
  - Enhanced user registration and login flows
  - Added new views: `RegisterView`, `EmailVerifyView`, `LoginView`, `RefreshTokenView`, `LogoutView`, `ForgotPasswordView`, `VerifyOTPView`, `ResetPasswordView`
- Updated `users/urls.py` to include new URL patterns:
  - `/register/` - User registration
  - `/verify-email/` - Email verification
  - `/login/` - User login
  - `/refresh/` - Token refresh
  - `/logout/` - User logout
  - `/forgot-password/` - Password reset request
  - `/verify-otp/` - OTP verification
  - `/reset-password/` - Password reset
- Updated `users/models.py`:
  - Added `is_verified` field to User model
  - Changed `is_active` default to False for new users
  - Added `EmailVerification` model for email verification codes
  - Added `PasswordResetOTP` model for password reset OTPs
- Updated `users/serializers.py`:
  - Replaced `UserRegistrationSerializer` with `RegisterSerializer`
  - Replaced `UserLoginSerializer` with `UserSerializer` (extends TokenObtainPairSerializer)
  - Added `EmailVerificationSerializer` for email verification
  - Added `PasswordResetOTPSerializer` for OTP verification
  - Added `PasswordResetSerializer` for password reset
- Replaced the Products model in Prouducts/models.py with new models: Category, Tag, Product (excluding brand, material, gender, sku), and ProductImage.

### Added
- `users/services.py` - Django SMTP email service (`EmailService`)
- `email_templates/verification_email.html` - Email verification template with proper Django syntax
- `email_templates/password_reset_email.html` - Password reset template with proper Django syntax
- Django SMTP email configuration in settings
- Error handling for email service failures
- Gmail SMTP setup guidance in email scripts
- Template directory configuration for email templates

### Removed
- MailerSend API integration and configuration
- `MailerSendService` class
- MailerSend-specific error handling (MS42225, MS42207)
- `mailersend` dependency from requirements.txt
- Old `UserRegistrationView` and `UserLoginView` classes
- Previous authentication implementation using `UserRegistrationSerializer` and `UserLoginSerializer`
- Old URL patterns: `/signup/` and `/signin/` 
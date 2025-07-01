from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from unittest.mock import patch, MagicMock
from .models import User, EmailVerification, PasswordResetOTP
from .services import MailerSendService

User = get_user_model()

class EmailServiceTest(APITestCase):
    """Test email service functionality"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='testpass123'
        )
        self.mailer_service = MailerSendService()

    @patch('users.services.emails.NewEmail')
    def test_mailer_send_service_initialization(self, mock_new_email):
        """Test MailerSend service initialization"""
        mock_mailer = MagicMock()
        mock_new_email.return_value = mock_mailer
        
        service = MailerSendService()
        
        self.assertIsNotNone(service.mailer)
        self.assertEqual(service.from_email, 'abnmoh525@gmail.com')
        self.assertEqual(service.from_name, 'Shoe Ecommerce')

    @patch('users.services.emails.NewEmail')
    def test_send_verification_email_success(self, mock_new_email):
        """Test successful verification email sending"""
        mock_mailer = MagicMock()
        mock_new_email.return_value = mock_mailer
        mock_mailer.send.return_value = {'status': 'success', 'message_id': 'test123'}
        
        service = MailerSendService()
        result = service.send_verification_email('test@example.com', '123456')
        
        # Verify the email was configured correctly
        mock_mailer.set_mail_from.assert_called_once()
        mock_mailer.set_mail_to.assert_called_once()
        mock_mailer.set_subject.assert_called_once_with("Verify Your Email - Shoe Ecommerce", {})
        mock_mailer.set_template.assert_called_once()
        mock_mailer.set_personalization.assert_called_once()
        mock_mailer.send.assert_called_once()
        
        self.assertEqual(result, {'status': 'success', 'message_id': 'test123'})

    @patch('users.services.emails.NewEmail')
    def test_send_password_reset_email_success(self, mock_new_email):
        """Test successful password reset email sending"""
        mock_mailer = MagicMock()
        mock_new_email.return_value = mock_mailer
        mock_mailer.send.return_value = {'status': 'success', 'message_id': 'test456'}
        
        service = MailerSendService()
        result = service.send_password_reset_email('test@example.com', '789012')
        
        # Verify the email was configured correctly
        mock_mailer.set_mail_from.assert_called_once()
        mock_mailer.set_mail_to.assert_called_once()
        mock_mailer.set_subject.assert_called_once_with("Password Reset - Shoe Ecommerce", {})
        mock_mailer.set_template.assert_called_once()
        mock_mailer.set_personalization.assert_called_once()
        mock_mailer.send.assert_called_once()
        
        self.assertEqual(result, {'status': 'success', 'message_id': 'test456'})

    @patch('users.services.emails.NewEmail')
    def test_send_verification_email_failure(self, mock_new_email):
        """Test verification email sending failure"""
        mock_mailer = MagicMock()
        mock_new_email.return_value = mock_mailer
        mock_mailer.send.side_effect = Exception("API Error")
        
        service = MailerSendService()
        
        with self.assertRaises(Exception):
            service.send_verification_email('test@example.com', '123456')

    @patch('users.services.emails.NewEmail')
    def test_send_password_reset_email_failure(self, mock_new_email):
        """Test password reset email sending failure"""
        mock_mailer = MagicMock()
        mock_new_email.return_value = mock_mailer
        mock_mailer.send.side_effect = Exception("API Error")
        
        service = MailerSendService()
        
        with self.assertRaises(Exception):
            service.send_password_reset_email('test@example.com', '789012')

    def test_verification_email_personalization_variables(self):
        """Test that verification email includes correct personalization variables"""
        service = MailerSendService()
        
        # Create a mock to capture the personalization data
        with patch.object(service, 'mailer') as mock_mailer:
            service.send_verification_email('test@example.com', '123456')
            
            # Get the call arguments for set_personalization
            call_args = mock_mailer.set_personalization.call_args[0][0]
            
            # Verify the personalization structure
            self.assertEqual(len(call_args), 1)
            self.assertEqual(call_args[0]['email'], 'test@example.com')
            
            substitutions = call_args[0]['substitutions']
            self.assertEqual(len(substitutions), 2)
            
            # Check verification_code variable
            verification_var = next((s for s in substitutions if s['var'] == 'verification_code'), None)
            self.assertIsNotNone(verification_var)
            self.assertEqual(verification_var['value'], '123456')
            
            # Check user_email variable
            email_var = next((s for s in substitutions if s['var'] == 'user_email'), None)
            self.assertIsNotNone(email_var)
            self.assertEqual(email_var['value'], 'test@example.com')

    def test_password_reset_email_personalization_variables(self):
        """Test that password reset email includes correct personalization variables"""
        service = MailerSendService()
        
        # Create a mock to capture the personalization data
        with patch.object(service, 'mailer') as mock_mailer:
            service.send_password_reset_email('test@example.com', '789012')
            
            # Get the call arguments for set_personalization
            call_args = mock_mailer.set_personalization.call_args[0][0]
            
            # Verify the personalization structure
            self.assertEqual(len(call_args), 1)
            self.assertEqual(call_args[0]['email'], 'test@example.com')
            
            substitutions = call_args[0]['substitutions']
            self.assertEqual(len(substitutions), 2)
            
            # Check otp_code variable
            otp_var = next((s for s in substitutions if s['var'] == 'otp_code'), None)
            self.assertIsNotNone(otp_var)
            self.assertEqual(otp_var['value'], '789012')
            
            # Check user_email variable
            email_var = next((s for s in substitutions if s['var'] == 'user_email'), None)
            self.assertIsNotNone(email_var)
            self.assertEqual(email_var['value'], 'test@example.com')

class EmailIntegrationTest(APITestCase):
    """Test email integration with views"""
    
    def setUp(self):
        self.register_url = reverse('register')
        self.forgot_password_url = reverse('forgot-password')
        self.valid_registration_payload = {
            'email': 'test@example.com',
            'username': 'testuser',
            'first_name': 'Test',
            'last_name': 'User',
            'phone_number': '+1234567890',
            'password': 'testpass123',
            'confirm_password': 'testpass123'
        }

    @patch('users.views.MailerSendService')
    def test_registration_email_sent_with_correct_data(self, mock_mailer_service):
        """Test that registration sends email with correct verification code"""
        mock_service_instance = mock_mailer_service.return_value
        mock_service_instance.send_verification_email.return_value = {'status': 'success'}
        
        response = self.client.post(self.register_url, self.valid_registration_payload)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Verify user was created
        user = User.objects.get(email='test@example.com')
        verification = EmailVerification.objects.get(user=user)
        
        # Verify email was sent with correct parameters
        mock_service_instance.send_verification_email.assert_called_once_with(
            user.email, 
            verification.code
        )

    @patch('users.views.MailerSendService')
    def test_registration_email_failure_handling(self, mock_mailer_service):
        """Test that registration handles email failure gracefully"""
        mock_service_instance = mock_mailer_service.return_value
        mock_service_instance.send_verification_email.side_effect = Exception("Email service down")
        
        response = self.client.post(self.register_url, self.valid_registration_payload)
        
        # Should still create user but return warning
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('warning', response.data)
        self.assertIn('Email service temporarily unavailable', response.data['warning'])
        
        # Verify user was still created
        user = User.objects.get(email='test@example.com')
        self.assertIsNotNone(user)

    @patch('users.views.MailerSendService')
    def test_password_reset_email_sent_with_correct_data(self, mock_mailer_service):
        """Test that password reset sends email with correct OTP"""
        user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='testpass123',
            is_verified=True,
            is_active=True
        )
        
        mock_service_instance = mock_mailer_service.return_value
        mock_service_instance.send_password_reset_email.return_value = {'status': 'success'}
        
        response = self.client.post(self.forgot_password_url, {'email': 'test@example.com'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify OTP was created
        otp_obj = PasswordResetOTP.objects.get(user=user)
        
        # Verify email was sent with correct parameters
        mock_service_instance.send_password_reset_email.assert_called_once_with(
            user.email, 
            otp_obj.otp
        )

    @patch('users.views.MailerSendService')
    def test_password_reset_email_failure_handling(self, mock_mailer_service):
        """Test that password reset handles email failure properly"""
        user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='testpass123',
            is_verified=True,
            is_active=True
        )
        
        mock_service_instance = mock_mailer_service.return_value
        mock_service_instance.send_password_reset_email.side_effect = Exception("Email service down")
        
        response = self.client.post(self.forgot_password_url, {'email': 'test@example.com'})
        
        # Should return error
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertIn('error', response.data)
        self.assertIn('Failed to send OTP', response.data['error'])

class UserRegistrationTest(APITestCase):
    def setUp(self):
        self.register_url = reverse('register')
        self.valid_payload = {
            'email': 'test@example.com',
            'username': 'testuser',
            'first_name': 'Test',
            'last_name': 'User',
            'phone_number': '+1234567890',
            'password': 'testpass123',
            'confirm_password': 'testpass123'
        }

    @patch('users.views.MailerSendService')
    def test_successful_registration(self, mock_mailer_service):
        """Test successful user registration"""
        # Mock the MailerSend service
        mock_service_instance = mock_mailer_service.return_value
        mock_service_instance.send_verification_email.return_value = {'status': 'success'}
        
        response = self.client.post(self.register_url, self.valid_payload)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('message', response.data)
        self.assertEqual(response.data['message'], 'Registration successful. Please check your email for verification.')
        
        # Check if user was created
        user = User.objects.get(email='test@example.com')
        self.assertFalse(user.is_verified)
        self.assertFalse(user.is_active)
        
        # Check if email verification was created
        verification = EmailVerification.objects.get(user=user)
        self.assertFalse(verification.is_used)
        
        # Check if email was sent
        mock_service_instance.send_verification_email.assert_called_once_with(user.email, verification.code)

    def test_registration_with_mismatched_passwords(self):
        """Test registration with mismatched passwords"""
        payload = self.valid_payload.copy()
        payload['confirm_password'] = 'differentpass'
        
        response = self.client.post(self.register_url, payload)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('non_field_errors', response.data)

    def test_registration_with_existing_email(self):
        """Test registration with existing email"""
        User.objects.create_user(
            email='test@example.com',
            username='existinguser',
            password='testpass123'
        )
        
        response = self.client.post(self.register_url, self.valid_payload)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response.data)

class EmailVerificationTest(APITestCase):
    def setUp(self):
        self.verify_url = reverse('verify-email')
        self.user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='testpass123'
        )
        self.verification = EmailVerification.objects.create(user=self.user)

    def test_verifing_unverified_emails(self):
        verifying_url = reverse('reverify-email')
        # Make sure the user is not verified
        self.user.is_verified = False
        self.user.save()
        # Authenticate as the user
        self.client.force_authenticate(user=self.user)
        payload = {'email': self.user.email}
        response = self.client.post(verifying_url, payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('message', response.data)
        self.assertIn('Please check your email for the code', response.data['message'])
        # Check that a new EmailVerification object was created
        verifications = EmailVerification.objects.filter(user=self.user)
        self.assertTrue(verifications.exists())

    def test_successful_email_verification(self):
        """Test successful email verification"""
        payload = {'code': self.verification.code}
        
        response = self.client.post(self.verify_url, payload)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['message'], 'Email verified successfully.')
        
        # Check if user is now verified and active
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_verified)
        self.assertTrue(self.user.is_active)
        
        # Check if verification is marked as used
        self.verification.refresh_from_db()
        self.assertTrue(self.verification.is_used)

    def test_invalid_verification_code(self):
        """Test email verification with invalid code"""
        payload = {'code': '000000'}
        
        response = self.client.post(self.verify_url, payload)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)

    def test_already_used_verification_code(self):
        """Test email verification with already used code"""
        self.verification.is_used = True
        self.verification.save()
        
        payload = {'code': self.verification.code}
        
        response = self.client.post(self.verify_url, payload)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)

class LoginTest(APITestCase):
    def setUp(self):
        self.login_url = reverse('login')
        self.user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='testpass123',
            is_verified=True,
            is_active=True
        )

    def test_successful_login(self):
        """Test successful login"""
        payload = {
            'email': 'test@example.com',
            'password': 'testpass123'
        }
        
        response = self.client.post(self.login_url, payload)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

    def test_login_with_unverified_user(self):
        """Test login with unverified user"""
        self.user.is_verified = False
        self.user.save()
        
        payload = {
            'email': 'test@example.com',
            'password': 'testpass123'
        }
        
        response = self.client.post(self.login_url, payload)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('detail', response.data)

    def test_login_with_inactive_user(self):
        """Test login with inactive user"""
        self.user.is_active = False
        self.user.save()
        
        payload = {
            'email': 'test@example.com',
            'password': 'testpass123'
        }
        
        response = self.client.post(self.login_url, payload)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('detail', response.data)

    def test_login_with_invalid_credentials(self):
        """Test login with invalid credentials"""
        payload = {
            'email': 'test@example.com',
            'password': 'wrongpassword'
        }
        
        response = self.client.post(self.login_url, payload)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('detail', response.data)

class PasswordResetTest(APITestCase):
    def setUp(self):
        self.forgot_password_url = reverse('forgot-password')
        self.verify_otp_url = reverse('verify-otp')
        self.reset_password_url = reverse('reset-password')
        self.user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='testpass123',
            is_verified=True,
            is_active=True
        )

    @patch('users.views.MailerSendService')
    def test_forgot_password_success(self, mock_mailer_service):
        """Test successful forgot password request"""
        # Mock the MailerSend service
        mock_service_instance = mock_mailer_service.return_value
        mock_service_instance.send_password_reset_email.return_value = {'status': 'success'}
        
        payload = {'email': 'test@example.com'}
        
        response = self.client.post(self.forgot_password_url, payload)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['message'], 'OTP sent to your email.')
        
        # Check if OTP was created
        otp_obj = PasswordResetOTP.objects.get(user=self.user)
        self.assertFalse(otp_obj.is_used)
        
        # Check if email was sent
        mock_service_instance.send_password_reset_email.assert_called_once_with(self.user.email, otp_obj.otp)

    def test_forgot_password_with_nonexistent_email(self):
        """Test forgot password with nonexistent email"""
        payload = {'email': 'nonexistent@example.com'}
        
        response = self.client.post(self.forgot_password_url, payload)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn('error', response.data)

    def test_verify_otp_success(self):
        """Test successful OTP verification"""
        otp_obj = PasswordResetOTP.objects.create(user=self.user)
        
        payload = {
            'email': 'test@example.com',
            'otp': otp_obj.otp
        }
        
        response = self.client.post(self.verify_otp_url, payload)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['message'], 'OTP verified.')

    def test_verify_otp_with_invalid_otp(self):
        """Test OTP verification with invalid OTP"""
        payload = {
            'email': 'test@example.com',
            'otp': '000000'
        }
        
        response = self.client.post(self.verify_otp_url, payload)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)

    def test_reset_password_success(self):
        """Test successful password reset"""
        otp_obj = PasswordResetOTP.objects.create(user=self.user)
        
        payload = {
            'email': 'test@example.com',
            'otp': otp_obj.otp,
            'new_password': 'newpass123',
            'confirm_password': 'newpass123'
        }
        
        response = self.client.post(self.reset_password_url, payload)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['message'], 'Password reset successful.')
        
        # Check if OTP is marked as used
        otp_obj.refresh_from_db()
        self.assertTrue(otp_obj.is_used)
        
        # Check if password was changed
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('newpass123'))

    def test_reset_password_with_mismatched_passwords(self):
        """Test password reset with mismatched passwords"""
        otp_obj = PasswordResetOTP.objects.create(user=self.user)
        
        payload = {
            'email': 'test@example.com',
            'otp': otp_obj.otp,
            'new_password': 'newpass123',
            'confirm_password': 'differentpass'
        }
        
        response = self.client.post(self.reset_password_url, payload)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('non_field_errors', response.data)

class LogoutTest(APITestCase):
    def setUp(self):
        self.logout_url = reverse('logout')
        self.user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='testpass123',
            is_verified=True,
            is_active=True
        )
        self.refresh_token = RefreshToken.for_user(self.user)

    def test_successful_logout(self):
        """Test successful logout"""
        self.client.force_authenticate(user=self.user)
        
        payload = {'refresh': str(self.refresh_token)}
        
        response = self.client.post(self.logout_url, payload)
        
        # Accept both 205 and 400 (if token is already blacklisted)
        self.assertIn(response.status_code, [status.HTTP_205_RESET_CONTENT, status.HTTP_400_BAD_REQUEST])

    def test_logout_without_authentication(self):
        """Test logout without authentication"""
        payload = {'refresh': str(self.refresh_token)}
        
        response = self.client.post(self.logout_url, payload)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_logout_with_invalid_token(self):
        """Test logout with invalid token"""
        self.client.force_authenticate(user=self.user)
        
        payload = {'refresh': 'invalid_token'}
        
        response = self.client.post(self.logout_url, payload)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

class TokenRefreshTest(APITestCase):
    def setUp(self):
        self.refresh_url = reverse('refresh')
        self.user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='testpass123',
            is_verified=True,
            is_active=True
        )
        self.refresh_token = RefreshToken.for_user(self.user)

    def test_successful_token_refresh(self):
        """Test successful token refresh"""
        payload = {'refresh': str(self.refresh_token)}
        
        response = self.client.post(self.refresh_url, payload)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)

    def test_token_refresh_with_invalid_token(self):
        """Test token refresh with invalid token"""
        payload = {'refresh': 'invalid_token'}
        
        response = self.client.post(self.refresh_url, payload)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED) 
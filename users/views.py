from django.contrib.auth import get_user_model
from django.contrib.auth import authenticate
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .models import User, EmailVerification, PasswordResetOTP
from .serializers import (
    RegisterSerializer, EmailVerificationSerializer, PasswordResetOTPSerializer, PasswordResetSerializer, UserSerializer,VerifyingEmailForUnVerifiedSerializer
)
from .services import EmailService
import random
import logging

# Set up logger
logger = logging.getLogger(__name__)

User = get_user_model()

# Create your views here.

class RegisterView(APIView):
    permission_classes = [permissions.AllowAny]
    def post(self, request):
        logger.info("=== Starting user registration process ===")
        
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            logger.info("Serializer validation successful")
            
            try:
                user = serializer.save()
                logger.info(f"User created successfully with email: {user.email}")
                
                # Create email verification
                verification = EmailVerification.objects.create(user=user)
                logger.info(f"Email verification object created with code: {verification.code}")
                
                # Send email using Django SMTP
                logger.info("=== Starting email sending process ===")
                logger.info(f"Attempting to send verification email to: {user.email}")
                logger.info(f"Verification code: {verification.code}")
                
                email_service = EmailService()
                logger.info("EmailService initialized successfully")
                
                try:
                    logger.info("Calling email_service.send_verification_email()...")
                    result = email_service.send_verification_email(user.email, verification.code)
                    logger.info(f"Email service returned: {result}")
                    logger.info("=== Email sent successfully ===")
                    
                    return Response({'message': 'Registration successful. Please check your email for verification.'}, status=status.HTTP_201_CREATED)
                    
                except Exception as e:
                    logger.error(f"=== Email sending failed ===")
                    logger.error(f"Exception type: {type(e).__name__}")
                    logger.error(f"Exception message: {str(e)}")
                    logger.error(f"Exception details: {e}")
                    
                    # Log additional debugging information
                    import traceback
                    logger.error(f"Full traceback: {traceback.format_exc()}")
                    
                    # If email fails, still create user but return warning
                    logger.warning("User created but email verification failed - returning warning response")
                    return Response({
                        'message': 'Registration successful but email verification failed. Please contact support.',
                        'warning': 'Email service temporarily unavailable',
                        'debug_info': {
                            'error_type': type(e).__name__,
                            'error_message': str(e)
                        }
                    }, status=status.HTTP_201_CREATED)
                    
            except Exception as user_creation_error:
                logger.error(f"=== User creation failed ===")
                logger.error(f"Error creating user: {user_creation_error}")
                logger.error(f"Full traceback: {traceback.format_exc()}")
                return Response({'error': 'Failed to create user account.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
        else:
            logger.error(f"Serializer validation failed: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class VerifyingEmailForUnVerified(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def post (self,request):
        email=request.data.get('email')
        serializer = VerifyingEmailForUnVerifiedSerializer(data=request.data)
        if serializer.is_valid():
            user=User.objects.get(email=email)
            verification = EmailVerification.objects.create(user=user)
            email_service = EmailService()
            logger.info("EmailService initialized successfully")
                
            try:
                logger.info("Calling email_service.send_verification_email()...")
                result = email_service.send_verification_email(user.email, verification.code)
                return Response({'message': 'Verifaction code sucsessed. Please check your email for the code.'}, status=status.HTTP_200_OK)
            except Exception as e:
                return Response({
                        'message': 'The verifiction faild plese try agin after 30 minutes.',
                        'warning': 'Email service temporarily unavailable',
                        'debug_info': {
                            'error_type': type(e).__name__,
                            'error_message': str(e)
                        }
                    }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)       
            
class EmailVerifyView(APIView):
    permission_classes = [permissions.AllowAny]
    def post(self, request):
        code = request.data.get('code')
        try:
            verification = EmailVerification.objects.get(code=code, is_used=False)
            verification.is_used = True
            verification.save()
            verification.user.is_verified = True
            verification.user.is_active = True
            verification.user.save()
            return Response({'message': 'Email verified successfully.'}, status=status.HTTP_200_OK)
        except EmailVerification.DoesNotExist:
            return Response({'error': 'Invalid or expired verification code.'}, status=status.HTTP_400_BAD_REQUEST)

class LoginView(TokenObtainPairView):
    permission_classes = [permissions.AllowAny]

class RefreshTokenView(TokenRefreshView):
    permission_classes = [permissions.AllowAny]

class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def post(self, request):
        try:
            refresh_token = request.data["refresh"]
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response(status=status.HTTP_205_RESET_CONTENT)
        except Exception:
            return Response(status=status.HTTP_400_BAD_REQUEST)

class ForgotPasswordView(APIView):
    permission_classes = [permissions.AllowAny]
    def post(self, request):
        email = request.data.get('email')
        try:
            user = User.objects.get(email=email)
            otp = f"{random.randint(100000, 999999)}"
            PasswordResetOTP.objects.create(user=user, otp=otp)
            # Send email using Django SMTP
            email_service = EmailService()
            try:
                email_service.send_password_reset_email(user.email, otp)
                return Response({'message': 'OTP sent to your email.'}, status=status.HTTP_200_OK)
            except Exception as e:
                return Response({'error': 'Failed to send OTP. Please try again.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except User.DoesNotExist:
            return Response({'error': 'User with this email does not exist.'}, status=status.HTTP_404_NOT_FOUND)

class VerifyOTPView(APIView):
    permission_classes = [permissions.AllowAny]
    def post(self, request):
        email = request.data.get('email')
        otp = request.data.get('otp')
        try:
            user = User.objects.get(email=email)
            otp_obj = PasswordResetOTP.objects.filter(user=user, otp=otp, is_used=False).last()
            if otp_obj and otp_obj.is_valid():
                # Mark OTP as used if you want
                # otp_obj.is_used = True
                # otp_obj.save()
                # Issue JWT token
                refresh = RefreshToken.for_user(user)
                return Response({
                    'message': 'OTP verified.',
                    'refresh': str(refresh),
                    'access': str(refresh.access_token)
                }, status=status.HTTP_200_OK)
            return Response({'error': 'Invalid or expired OTP.'}, status=status.HTTP_400_BAD_REQUEST)
        except User.DoesNotExist:
            return Response({'error': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)

class ResetPasswordView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def post(self, request):
        # Use the authenticated user from the token
        user = request.user
        serializer = PasswordResetSerializer(data=request.data)
        
        if serializer.is_valid():
            otp = serializer.validated_data['otp']
            new_password = serializer.validated_data['new_password']
            
            try:
                otp_obj = PasswordResetOTP.objects.filter(user=user, otp=otp, is_used=False).last()
                if otp_obj and otp_obj.is_valid():
                    user.set_password(new_password)
                    user.save()
                    otp_obj.is_used = True
                    otp_obj.save()
                    return Response({'message': 'Password reset successful.'}, status=status.HTTP_200_OK)
                return Response({'error': 'Invalid or expired OTP.'}, status=status.HTTP_400_BAD_REQUEST)
            except Exception as e:
                logger.error(f"Error resetting password: {e}")
                return Response({'error': 'Error resetting password.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

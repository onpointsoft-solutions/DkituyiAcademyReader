from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
import logging

logger = logging.getLogger(__name__)

class EmailService:
    """Email service for dkituyi academy with digital reading branding"""
    
    @staticmethod
    def send_welcome_email(user_email, user_name, user_id):
        """Send welcome email to new users"""
        try:
            subject = "Welcome to dkituyi academy - Your Digital Reading Journey Begins!"
            
            html_message = render_to_string('emails/welcome.html', {
                'user_name': user_name,
                'user_email': user_email,
                'user_id': user_id,
                'academy_name': 'dkituyi academy',
                'tagline': 'Celebrating Great Literature & Digital Reading'
            })
            
            plain_message = strip_tags(html_message)
            
            send_mail(
                subject=subject,
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user_email],
                html_message=html_message,
                fail_silently=False
            )
            
            logger.info(f"Welcome email sent to {user_email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send welcome email to {user_email}: {str(e)}")
            return False
    
    @staticmethod
    def send_book_notification(user_email, book_title, author_name, book_description):
        """Send notification when new books are added"""
        try:
            subject = f"New Book Available: {book_title} - dkituyi academy"
            
            html_message = render_to_string('emails/new_book.html', {
                'book_title': book_title,
                'author_name': author_name,
                'book_description': book_description,
                'academy_name': 'dkituyi academy',
                'tagline': 'Celebrating Great Literature & Digital Reading'
            })
            
            plain_message = strip_tags(html_message)
            
            send_mail(
                subject=subject,
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user_email],
                html_message=html_message,
                fail_silently=False
            )
            
            logger.info(f"Book notification sent to {user_email} for {book_title}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send book notification to {user_email}: {str(e)}")
            return False
    
    @staticmethod
    def send_password_reset_email(user_email, reset_link, user_name):
        """Send password reset email"""
        try:
            subject = "Reset Your Password - dkituyi academy"
            
            html_message = render_to_string('emails/password_reset.html', {
                'user_name': user_name,
                'reset_link': reset_link,
                'academy_name': 'dkituyi academy',
                'tagline': 'Celebrating Great Literature & Digital Reading'
            })
            
            plain_message = strip_tags(html_message)
            
            send_mail(
                subject=subject,
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user_email],
                html_message=html_message,
                fail_silently=False
            )
            
            logger.info(f"Password reset email sent to {user_email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send password reset email to {user_email}: {str(e)}")
            return False
    
    @staticmethod
    def send_subscription_confirmation(user_email, plan_name, amount, start_date, end_date):
        """Send subscription confirmation email"""
        try:
            subject = f"Subscription Confirmed - {plan_name} - dkituyi academy"
            
            html_message = render_to_string('emails/subscription_confirmed.html', {
                'plan_name': plan_name,
                'amount': amount,
                'start_date': start_date,
                'end_date': end_date,
                'academy_name': 'dkituyi academy',
                'tagline': 'Celebrating Great Literature & Digital Reading'
            })
            
            plain_message = strip_tags(html_message)
            
            send_mail(
                subject=subject,
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user_email],
                html_message=html_message,
                fail_silently=False
            )
            
            logger.info(f"Subscription confirmation sent to {user_email} for {plan_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send subscription confirmation to {user_email}: {str(e)}")
            return False
    
    @staticmethod
    def send_admin_notification(subject, message, admin_emails=None):
        """Send notification to admin users"""
        try:
            if admin_emails is None:
                admin_emails = [settings.ADMIN_EMAIL]
            
            html_message = render_to_string('emails/admin_notification.html', {
                'subject': subject,
                'message': message,
                'academy_name': 'dkituyi academy',
                'tagline': 'Celebrating Great Literature & Digital Reading'
            })
            
            plain_message = strip_tags(html_message)
            
            send_mail(
                subject=f"[Admin Alert] {subject} - dkituyi academy",
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=admin_emails,
                html_message=html_message,
                fail_silently=False
            )
            
            logger.info(f"Admin notification sent: {subject}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send admin notification: {str(e)}")
            return False

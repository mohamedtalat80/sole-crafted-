# 📧 Django SMTP Email Scripts

This directory contains Python scripts for sending emails using Django's SMTP backend with Gmail.

## 📋 Prerequisites

1. **Gmail Account**: A Gmail account with 2-factor authentication enabled
2. **App Password**: Generate an app password for your Gmail account
3. **Django Project**: This project must be set up with Django
4. **Python Dependencies**: Install required packages

## 🚀 Installation

### 1. Install Dependencies

```bash
pip install python-decouple python-dotenv
```

### 2. Set Up Gmail App Password

1. **Enable 2-Factor Authentication**:
   - Go to your Google Account settings
   - Navigate to Security → 2-Step Verification
   - Enable 2-factor authentication

2. **Generate App Password**:
   - Go to Google Account → Security → App Passwords
   - Select "Mail" as the app
   - Generate the password
   - Copy the 16-character password

### 3. Set Up Environment Variables

Create a `.env` file in your project root:

```env
EMAIL_HOST_PASSWORD=your_gmail_app_password_here
```

Replace `your_gmail_app_password_here` with your actual Gmail app password.

## 📁 Scripts Overview

### 1. `simple_email_sender.py` - Basic Email Sender

A simple script for sending basic emails using Django SMTP.

**Features:**
- Interactive input for recipient, subject, and message
- HTML email support
- Gmail SMTP error handling
- Setup validation

**Usage:**
```bash
python simple_email_sender.py
```

**Example Output:**
```
📧 Simple Django SMTP Email Sender
========================================
🔍 Checking Gmail SMTP Setup...
==================================================
✅ Email Host User: abnmoh525@gmail.com
✅ App Password found

📋 Setup Checklist:
   1. ✅ Email host user configured
   2. ✅ App password configured
   3. ⏳ 2-factor authentication enabled
   4. ⏳ App password generated

Enter recipient email: user@example.com
Enter email subject (or press Enter for default): Hello from Shoe Ecommerce!
Enter email message (or press Enter for default): This is a test email!

📧 Sending email to user@example.com...
✅ Email sent successfully!
📊 Result: 1

🎉 Email sent successfully!
📝 Check the recipient's inbox for the email.
```

## 🔧 Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `EMAIL_HOST_PASSWORD` | Your Gmail app password | ✅ Yes |

### Email Configuration

The scripts use these Gmail SMTP settings:
- **Host**: `smtp.gmail.com`
- **Port**: `587`
- **TLS**: `True`
- **From Email**: `abnmoh525@gmail.com`
- **From Name**: `Shoe Ecommerce`

## 🎨 Email Templates

### HTML Email Example

The script includes a simple HTML email template:

```html
<html>
<body>
    <h2>{subject}</h2>
    <p>{message}</p>
    <hr>
    <p><em>Sent from Shoe Ecommerce</em></p>
</body>
</html>
```

## 🚨 Error Handling

The script includes comprehensive error handling:

- **Missing App Password**: Clear error message with setup instructions
- **Authentication Errors**: Guidance for Gmail app password setup
- **SMTP Connection Errors**: Network and connection issue handling
- **Invalid Email**: Validation for recipient email addresses

## 🔒 Security Best Practices

1. **Never commit app passwords** to version control
2. **Use environment variables** for sensitive data
3. **Enable 2-factor authentication** on your Gmail account
4. **Use app passwords** instead of your regular password
5. **Validate email addresses** before sending
6. **Monitor your Gmail account** for any security alerts

## 🛠️ Troubleshooting

### Common Issues

1. **"App Password not found"**
   - Check your `.env` file exists
   - Verify `EMAIL_HOST_PASSWORD` is set correctly
   - Make sure you're using an app password, not your regular password

2. **"Authentication failed" error**
   - Verify your app password is correct
   - Make sure 2-factor authentication is enabled
   - Generate a new app password if needed

3. **"SMTP connection failed" error**
   - Check your internet connection
   - Verify Gmail SMTP is not blocked by firewall
   - Check if Gmail account is active

4. **"Invalid sender" error**
   - Verify the sender email matches your Gmail account
   - Check if your Gmail account is properly configured

### Gmail Setup Steps

1. **Enable 2-Factor Authentication**:
   ```
   1. Go to Google Account settings
   2. Security → 2-Step Verification
   3. Enable 2-factor authentication
   ```

2. **Generate App Password**:
   ```
   1. Go to Google Account → Security → App Passwords
   2. Select "Mail" as the app
   3. Click "Generate"
   4. Copy the 16-character password
   ```

3. **Add to Environment**:
   ```
   1. Create .env file in project root
   2. Add: EMAIL_HOST_PASSWORD=your_app_password
   3. Restart your application
   ```

## 📈 Monitoring

### Check Email Status

After sending emails, you can monitor their status in:

1. **Gmail Sent Folder**: View sent emails
2. **Gmail Account Activity**: Check for any security alerts
3. **Recipient's Inbox**: Verify delivery to recipient

## 🎯 Best Practices

1. **Test with your own email first** before sending to others
2. **Use meaningful subjects** to avoid spam filters
3. **Keep email content professional** and well-formatted
4. **Monitor your Gmail account** for any issues
5. **Respect email sending limits** to avoid being flagged as spam
6. **Use HTML emails sparingly** and ensure they're mobile-friendly

## 🔄 Integration with Django

The email service is integrated with Django through:

- **Settings Configuration**: SMTP settings in `settings.py`
- **Email Service**: `users/services.py` with `EmailService` class
- **Views Integration**: Email sending in authentication views
- **Templates**: HTML email templates in `email_templates/`

---

**Need Help?** If you're still experiencing issues, check your Gmail account settings and ensure 2-factor authentication is properly configured. 
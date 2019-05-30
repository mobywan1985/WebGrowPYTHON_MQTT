# Python mail script with smtplib, email.utils and email.mime.text.

# --- imports ---

import smtplib
import email.utils
from email.mime.text import MIMEText

# --- create our message ---
class AlertMailer():
    default_email_address = ''
    sender_email = ''
    sender_password = ''
    sender_name  = 'WebGrow'
    email_subject = 'Device Alert'
    

    def __init__(self,default_email, sender_email, sender_pw):
        self.default_email_address = default_email
        self.sender_email = sender_email
        self.sender_password = sender_pw
        
    def send_mail(self, device, alert_msg):
        # Create our message. 
        msg = MIMEText('Device: '+device+' Alert!\n'+alert_msg)
        msg['To'] = email.utils.formataddr(('WebGrow Admin', self.default_email_address))
        msg['From'] = email.utils.formataddr(('WebGrow', self.sender_email))
        msg['Subject'] = 'Device Alert'

        # --- send the email ---

        # SMTP() is used with normal, unencrypted (non-SSL) email.
        # To send email via an SSL connection, use SMTP_SSL().
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(self.sender_email, self.sender_password)
        try:
            server.sendmail(self.sender_email, [self.default_email_address], msg.as_string())
        finally:
            server.quit()

import smtplib
from email.mime.text import MIMEText

from decouple import Csv, config


def send_email(msg_str):
    msg = MIMEText(msg_str)
    s = smtplib.SMTP(config("EMAIL_HOST"), 587)
    s.starttls()
    s.login(config("EMAIL_USER"), config("EMAIL_PASSWORD"))

    from_addr = config("FROM_EMAIL")
    to_addr = config("ADMIN_EMAILS", cast=Csv())
    msg["from"] = from_addr
    msg["to"] = ", ".join(to_addr)
    s.sendmail(from_addr, to_addr, msg.as_string())

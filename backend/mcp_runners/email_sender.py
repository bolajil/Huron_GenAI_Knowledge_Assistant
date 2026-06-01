import smtplib, ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


def run(config: dict, result_text: str, query: str, user_params: dict) -> dict:
    smtp_host = config.get("smtp_host", "smtp.gmail.com")
    smtp_port = int(config.get("smtp_port", 587))
    smtp_user = config.get("smtp_user")
    smtp_pass = config.get("smtp_password")
    from_addr = config.get("from_addr") or smtp_user
    to_addr   = user_params.get("recipient") or config.get("default_recipient")

    if not smtp_user or not smtp_pass:
        raise ValueError(
            "Email credentials are not configured for your department. "
            "Ask an admin to set SMTP settings under MCP → Manage Tools."
        )
    if not to_addr:
        raise ValueError("No recipient address provided.")

    subject = user_params.get("subject") or f"Query Result: {query[:60]}"
    body    = f"Query: {query}\n\n{result_text}"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = from_addr
    msg["To"]      = to_addr
    msg.attach(MIMEText(body, "plain"))

    ctx = ssl.create_default_context()
    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.ehlo()
        server.starttls(context=ctx)
        server.login(smtp_user, smtp_pass)
        server.sendmail(from_addr, to_addr, msg.as_string())

    return {"detail": f"Sent to {to_addr}"}

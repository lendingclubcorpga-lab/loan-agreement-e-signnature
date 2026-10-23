# Loan agreement generator

Lender creates an encrypted signing link; the borrower opens it, reviews, signs by typing their name, and downloads the PDF.

## Secrets (Streamlit Cloud: App settings -> Secrets)

```
ADMIN_PASSWORD = "choose-a-strong-password"
FERNET_KEY = "paste a generated key"
APP_URL = "https://your-app-name.streamlit.app"
```

Generate FERNET_KEY once with:

    python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

Keep the same key; changing it invalidates links already sent.

## Use
1. Open the app URL, enter the lender password.
2. Fill business, borrower and loan details, click Generate link, send the link.
3. The borrower signs and downloads the PDF.

Replace the "Lender to complete" blanks in the terms and have a lawyer review them for your state.

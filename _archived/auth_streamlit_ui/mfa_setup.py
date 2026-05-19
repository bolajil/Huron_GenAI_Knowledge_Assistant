import streamlit as st
import pyotp
import qrcode
import io
from PIL import Image
from app.auth.enterprise_auth_simple import enterprise_auth

# This should be moved to a more central user management location
def set_user_totp_secret(username: str, secret: str):
    """Stores the user's TOTP secret.
    
    NOTE: In a real application, this MUST be stored securely in a database,
    associated with the user's profile. Using session_state is for demonstration
    purposes only and is NOT secure or persistent.
    """
    st.session_state[f"totp_secret_{username}"] = secret

def get_user_totp_secret(username: str) -> str:
    """Retrieves the user's TOTP secret."""
    return st.session_state.get(f"totp_secret_{username}", "")

def render_mfa_setup_page():
    """Renders the page for users to set up their TOTP authenticator app."""
    st.markdown("### 📱 Set Up Multi-Factor Authentication")
    st.info("Scan the QR code with your authenticator app (e.g., Google Authenticator, Authy).")

    user_data = st.session_state.get("user")
    if not user_data:
        st.error("User not found in session. Please log in again.")
        return

    username = user_data.get("username")
    
    # Generate a new secret if one doesn't exist for this session
    # In a real app, you'd check the database
    secret = get_user_totp_secret(username)
    if not secret:
        secret = pyotp.random_base32()
        set_user_totp_secret(username, secret) # Temporarily store for setup process

    # Generate provisioning URI
    provisioning_uri = pyotp.totp.TOTP(secret).provisioning_uri(
        name=username,
        issuer_name="VaultMind GenAI"
    )

    # Generate QR code
    qr_img = qrcode.make(provisioning_uri)
    buffered = io.BytesIO()
    qr_img.save(buffered, format="PNG")
    
    col1, col2 = st.columns([1, 2])
    with col1:
        st.image(buffered)

    with col2:
        st.markdown("#### Can't scan the code?")
        st.markdown("You can manually enter the setup key into your authenticator app:")
        st.code(secret, language="")

    st.markdown("---")

    # Verification form
    st.markdown("#### Verify Your Device")
    st.warning("Once you have added the account to your app, enter the 6-digit code below to complete the setup.")

    with st.form("mfa_setup_verify"):
        code = st.text_input(
            "Authentication Code",
            placeholder="000000",
            max_chars=6
        )
        verify_button = st.form_submit_button("Complete Setup & Verify", type="primary")

        if verify_button and code:
            totp = pyotp.TOTP(secret)
            if totp.verify(code, valid_window=1):
                # On successful verification, permanently save the secret in the user DB.
                st.session_state['mfa_setup_complete'] = True
                
                # Clean up MFA setup state
                if 'mfa_setup_pending' in st.session_state:
                    del st.session_state['mfa_setup_pending']
                
                # Complete the login
                user_data = st.session_state.get("user")
                if enterprise_auth._complete_login(user_data):
                    st.rerun()
                else:
                    st.error("Failed to complete login after MFA setup.")
            else:
                st.error("❌ Invalid code. Please try again.")

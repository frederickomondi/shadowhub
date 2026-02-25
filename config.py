import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'shadowhub-secret-key-2024')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///shadowhub.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = 'static/uploads'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size

    # Crypto wallet addresses
    BTC_WALLET = 'bc1q827ktacxgqvsvv52x8sg24hx0lljqutr2zlsw8'
    XMR_WALLET = '83FvbAgPnBsV2ix45AqQDwNfYRzrmVS5MSkE8st2id1tE5omSoDmSt1bKMDYJkLGysJNnVrdXCFp6JRUd8z1fcre7pkhrXp'
    USDT_WALLET = 'TR7j6aFEPhwzJuzYQ5ePksbKESjR8gL6MG'
    TRX_WALLET = 'TR7j6aFEPhwzJuzYQ5ePksbKESjR8gL6MG'

    PAYMENT_TIMEOUT_MINUTES = 30

    # Support contact
    CONTACT_EMAIL = 'salesshadowhub@proton.me'

    # ── PGP / GPG Public Key ──────────────────────────────────────────────
    # Paste your full ASCII-armored public key block below.
    # Export from GPG:  gpg --armor --export salesshadowhub@proton.me
    # Export from Proton Mail: Settings → Encryption & Keys → Export Public Key
    # Replace the placeholder below with your real key, keeping the
    # -----BEGIN PGP PUBLIC KEY BLOCK----- / -----END PGP PUBLIC KEY BLOCK----- markers.
    PGP_PUBLIC_KEY = os.environ.get('PGP_PUBLIC_KEY', """-----BEGIN PGP PUBLIC KEY BLOCK-----

PASTE YOUR PUBLIC PGP KEY HERE
Export it from Proton Mail: Settings → Encryption & Keys → Export Public Key
Or from GPG CLI: gpg --armor --export salesshadowhub@proton.me

-----END PGP PUBLIC KEY BLOCK-----""")

    # Short fingerprint shown in footer / contact page (last 16 hex chars of your key ID)
    # Run:  gpg --fingerprint salesshadowhub@proton.me
    # Replace the value below with your real fingerprint.
    PGP_FINGERPRINT = os.environ.get('PGP_FINGERPRINT', 'XXXX XXXX XXXX XXXX  XXXX XXXX XXXX XXXX XXXX XXXX')

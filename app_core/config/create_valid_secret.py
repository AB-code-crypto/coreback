from cryptography.fernet import Fernet
print(f'\nPROVIDER_CREDENTIAL_MASTER_KEY="{Fernet.generate_key().decode()}"')

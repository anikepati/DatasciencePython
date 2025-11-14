import argparse
import getpass
import keyring

# Service name for storing credentials (change if needed)
SERVICE_NAME = "registration_app"

def add_credentials():
    """Add username and password to the system credential store."""
    username = input("Enter username: ")
    password = getpass.getpass("Enter password: ")
    
    keyring.set_password(SERVICE_NAME, "username", username)
    keyring.set_password(SERVICE_NAME, "password", password)
    
    print("Credentials added successfully.")

def remove_credentials():
    """Remove username and password from the system credential store."""
    try:
        keyring.delete_password(SERVICE_NAME, "username")
        keyring.delete_password(SERVICE_NAME, "password")
        print("Credentials removed successfully.")
    except keyring.errors.PasswordDeleteError:
        print("No credentials found to remove.")

def main():
    parser = argparse.ArgumentParser(description="Manage credentials in system store (Mac Keychain or Windows Credential Manager).")
    parser.add_argument("action", choices=["add", "remove"], help="Action to perform: add or remove credentials")
    
    args = parser.parse_args()
    
    if args.action == "add":
        add_credentials()
    elif args.action == "remove":
        remove_credentials()

if __name__ == "__main__":
    main()

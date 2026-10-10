from getpass import getpass
from werkzeug.security import generate_password_hash

password = getpass("Enter new development password: ")

password_hash = generate_password_hash(password)

print("\nGenerated password hash:")
print(password_hash)
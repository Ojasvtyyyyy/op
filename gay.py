import hashlib

password = "holyhellnewresponsejustdropped"
hashed = hashlib.sha256(password.encode()).hexdigest()
print(hashed)
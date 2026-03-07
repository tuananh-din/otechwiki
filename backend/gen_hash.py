from passlib.context import CryptContext
c = CryptContext(schemes=["bcrypt"], deprecated="auto")
h = c.hash("admin123")
print(h)

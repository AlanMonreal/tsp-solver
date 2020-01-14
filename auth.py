#from hashlib import pbkdf2_hmac
#from binascii import hexlify
#from hmac import compare_digest
from bcrypt import checkpw, hashpw, gensalt
from secrets import token_hex

def validateLogin(password, passhash): # New login func
    if checkpw(password.encode(), passhash.encode()):
        return token_hex()
    else:
        #raise BadLogin # TODO
        return None

'''
def login(password, passhash): # Obsolete in favor of bcrypt
    if compare_digest(hashPassword(password), passhash):
        token = token_hex()
        return token
    else:
        # Throw exception
        return None

def hashPassword(password, salt='quiken'): # Obsolete in favor of bcrypt
    return hexlify(pbkdf2_hmac('sha512', password.encode(), salt.encode(), 100000, 64))
'''

'''
def validateToken(): # Return unit
    unit = quiken.getUnit(self.quikenConfig['db'], token)
    if unit: return unit
    else: return None # TODO: throw exception to return error payload

def setPassword(username, password):
    quiken.updatePassword(self.quikenConfig['db'], username, self.hash(password))
'''


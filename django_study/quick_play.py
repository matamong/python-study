import secrets
import string

RANDOM_KOR_DOG_STRING_CHARS = '월왈멍왕밬컹캉왁빡망학꺵1234567890'
CSRF_SECRET_LENGTH = 32


class Crypto:
    def get_random_kor_dog_string(self, length=12, allowed_chars=RANDOM_KOR_DOG_STRING_CHARS):
        return ''.join(secrets.choice(allowed_chars) for i in range(length))

    def mask_cipher_secret(self, secret):
        mask = self.get_random_kor_dog_string()
        chars = string.ascii_letters + string.digits
        pairs = zip((chars.index(x) for x in secret), (chars.index(x) for x in mask))
        cipher = ''.join(chars[(x + y) % len(chars)] for x, y in pairs)
        return mask + cipher


if __name__ == "__main__":
    chars = 'abcdefghijklmnopqrstuvxyz'
    print('Quick...playing...')
    cp = Crypto()
    secret = cp.get_random_kor_dog_string
    print(secret)
    print(cp.mask_cipher_secret(secret))

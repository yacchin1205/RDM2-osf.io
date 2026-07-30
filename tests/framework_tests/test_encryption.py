# -*- coding: utf-8 -*-
import unittest

from framework.encryption import encrypt, decrypt, ensure_bytes

class EncryptionTestCase(unittest.TestCase):

    def test_ensure_bytes_encodes_no_unicode_in_string_type_str(self):
        my_value = 'hello'
        assert (isinstance(my_value, str))
        my_str = ensure_bytes(my_value)
        assert (isinstance(my_str, bytes))

    def test_ensure_bytes_encodes_unicode_in_string_type_str(self):
        my_value = 'hellü'
        assert (isinstance(my_value, str))
        my_str = ensure_bytes(my_value)
        assert (isinstance(my_str, bytes))

    def test_ensure_bytes_encodes_no_unicode_in_string_type_unicode(self):
        my_value = u'hello'
        assert (isinstance(my_value, str))
        my_str = ensure_bytes(my_value)
        assert (isinstance(my_str, bytes))

    def test_ensure_bytes_encodes_unicode_in_string_type_unicode(self):
        my_value = u'hellü'
        assert (isinstance(my_value, str))
        my_str = ensure_bytes(my_value)
        assert (isinstance(my_str, bytes))

    def test_encrypt_and_decrypt_no_unicode_in_string_type_str(self):
        my_value = 'hello'
        assert (isinstance(my_value, str))
        my_value_encrypted = encrypt(my_value)
        assert (isinstance(my_value_encrypted, bytes))

        my_value_decrypted = decrypt(my_value_encrypted)
        assert (isinstance(my_value_decrypted, bytes))
        assert (my_value_decrypted) == (ensure_bytes(my_value))

    def test_encrypt_and_decrypt_unicode_in_string_type_str(self):
        my_value = 'hellü'
        assert (isinstance(my_value, str))
        my_value_encrypted = encrypt(my_value)
        assert (isinstance(my_value_encrypted, bytes))

        my_value_decrypted = decrypt(my_value_encrypted)
        assert (my_value_decrypted) == (ensure_bytes(my_value))

        my_value = '찦차КЛМНО💁◕‿◕｡)╱i̲̬͇̪͙n̝̗͕v̟̜̘̦͟o̶̙̰̠kè͚̮̺̪̹̱̤  ǝɹol'
        assert (isinstance(my_value, str))
        my_value_encrypted = encrypt(my_value)
        my_value_decrypted = decrypt(my_value_encrypted)
        assert (isinstance(my_value_decrypted, bytes))
        assert (my_value_decrypted) == (ensure_bytes(my_value))

    def test_encrypt_and_decrypt_no_unicode_in_string_type_unicode(self):
        my_value = u'hello'
        assert (isinstance(my_value, str))
        my_value_encrypted = encrypt(my_value)
        assert (isinstance(my_value_encrypted, bytes))

        my_value_decrypted = decrypt(my_value_encrypted)
        assert (isinstance(my_value_decrypted, bytes))
        assert (my_value_decrypted) == (ensure_bytes(my_value))

    def test_encrypt_and_decrypt_unicode_in_string_type_unicode(self):
        my_value = u'hellü'
        assert (isinstance(my_value, str))
        my_value_encrypted = encrypt(my_value)
        assert (isinstance(my_value_encrypted, bytes))

        my_value_decrypted = decrypt(my_value_encrypted)
        assert (my_value_decrypted) == (ensure_bytes(my_value))

        my_value = u'찦차КЛМНО💁◕‿◕｡)╱i̲̬͇̪͙n̝̗͕v̟̜̘̦͟o̶̙̰̠kè͚̮̺̪̹̱̤  ǝɹol'
        assert (isinstance(my_value, str))
        my_value_encrypted = encrypt(my_value)
        my_value_decrypted = decrypt(my_value_encrypted)
        assert (isinstance(my_value_decrypted, bytes))
        assert (my_value_decrypted) == (ensure_bytes(my_value))

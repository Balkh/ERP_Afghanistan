import base64
import os


class Obfuscator:
    def __init__(self, key=None):
        if key is None:
            # Generate a random key if not provided
            self.key = os.urandom(32)
        else:
            self.key = key

    def obfuscate(self, text):
        if not isinstance(text, str):
            text = str(text)
        # Simple XOR obfuscation (not for production use, but for demonstration)
        obfuscated_bytes = bytearray()
        for i, char in enumerate(text.encode('utf-8')):
            obfuscated_bytes.append(char ^ self.key[i % len(self.key)])
        return base64.b64encode(obfuscated_bytes).decode('utf-8')

    def deobfuscate(self, obfuscated_text):
        try:
            data = base64.b64decode(obfuscated_text.encode('utf-8'))
            decoded_bytes = bytearray()
            for i, byte in enumerate(data):
                decoded_bytes.append(byte ^ self.key[i % len(self.key)])
            return decoded_bytes.decode('utf-8')
        except Exception:
            return None
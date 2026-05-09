import os
import json
from .obfuscator import Obfuscator


class EncryptedConfig:
    def __init__(self, key=None, config_file=None):
        """
        Initialize the EncryptedConfig.

        :param key: The encryption key. If None, a key will be generated from the environment variable 'PHARMACY_ERP_CONFIG_KEY'
                    or a default key will be used (not recommended for production).
        :param config_file: The file path to store the encrypted configuration. If None, it defaults to 'config.enc' in the current directory.
        """
        if key is None:
            # Try to get key from environment variable
            key_env = os.environ.get('PHARMACY_ERP_CONFIG_KEY')
            if key_env:
                self.key = key_env.encode('utf-8')
            else:
                # Generate a key and store it in a file in the user's home directory for persistence
                key_file = os.path.join(os.path.expanduser('~'), '.pharmacy_erp_config_key')
                if os.path.exists(key_file):
                    with open(key_file, 'rb') as f:
                        self.key = f.read()
                else:
                    self.key = os.urandom(32)
                    with open(key_file, 'wb') as f:
                        f.write(self.key)
        else:
            if isinstance(key, str):
                key = key.encode('utf-8')
            self.key = key

        self.obfuscator = Obfuscator(self.key)
        self.config_file = config_file or os.path.join(os.getcwd(), 'config.enc')
        self._config = {}

    def set(self, key, value):
        """
        Set a configuration value.

        :param key: The configuration key.
        :param value: The value to store (will be converted to string for obfuscation).
        """
        self._config[key] = str(value)

    def get(self, key, default=None):
        """
        Get a configuration value.

        :param key: The configuration key.
        :param default: The default value to return if the key is not found.
        :return: The obfuscated and then deobfuscated value, or default if not found.
        """
        if key in self._config:
            # The value is stored as a string, but we don't need to obfuscate in memory for this example.
            # In a more secure implementation, we would store the obfuscated version in memory and deobfuscate on get.
            # For simplicity, we store the plaintext in memory and obfuscate only when saving to file.
            return self._config[key]
        return default

    def obfuscate_value(self, value):
        """
        Obfuscate a value for storage.

        :param value: The value to obfuscate (string).
        :return: The obfuscated string.
        """
        return self.obfuscator.obfuscate(value)

    def deobfuscate_value(self, obfuscated_value):
        """
        Deobfuscate a value.

        :param obfuscated_value: The obfuscated string.
        :return: The deobfuscated string, or None if obfuscation fails.
        """
        return self.obfuscator.deobfuscate(obfuscated_value)

    def save(self, file_path=None):
        """
        Save the configuration to an encrypted file.

        :param file_path: The file path to save to. If None, uses the instance's config_file.
        """
        file_path = file_path or self.config_file
        # Obfuscate each value in the config
        obfuscated_config = {}
        for key, value in self._config.items():
            obfuscated_config[key] = self.obfuscator.obfuscate(value)

        # Write the obfuscated config as JSON
        with open(file_path, 'w') as f:
            json.dump(obfuscated_config, f, indent=2)

    def load(self, file_path=None):
        """
        Load the configuration from an encrypted file.

        :param file_path: The file path to load from. If None, uses the instance's config_file.
        :return: True if successful, False otherwise.
        """
        file_path = file_path or self.config_file
        if not os.path.exists(file_path):
            return False

        try:
            with open(file_path, 'r') as f:
                obfuscated_config = json.load(f)

            # Deobfuscate each value
            self._config = {}
            for key, obfuscated_value in obfuscated_config.items():
                deobfuscated_value = self.obfuscator.deobfuscate(obfuscated_value)
                if deobfuscated_value is not None:
                    self._config[key] = deobfuscated_value
                else:
                    # If deobfuscation fails, we might want to keep the obfuscated value or set to None.
                    # For simplicity, we set to None and hope the user notices.
                    self._config[key] = None
            return True
        except Exception as e:
            print(f"Error loading encrypted config: {e}")
            return False
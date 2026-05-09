import os
import sys
import tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from security.obfuscator import Obfuscator
from security.encrypted_config import EncryptedConfig
from security.tamper_detector import TamperDetector


def test_obfuscator():
    print("Testing Obfuscator...")
    obfuscator = Obfuscator(key=b'secretkey123456789012')  # 32 bytes
    original = "Hello, World! This is a secret message."
    obfuscated = obfuscator.obfuscate(original)
    deobfuscated = obfuscator.deobfuscate(obfuscated)
    assert deobfuscated == original, f"Obfuscation failed: expected {original}, got {deobfuscated}"
    print("  PASS: Obfuscation and deobfuscation work correctly.")


def test_encrypted_config():
    print("Testing EncryptedConfig...")
    with tempfile.TemporaryDirectory() as tmpdir:
        config_file = os.path.join(tmpdir, 'test_config.enc')
        config = EncryptedConfig(key=b'secretkey123456789012', config_file=config_file)
        config.set('database_url', 'postgresql://user:pass@localhost/db')
        config.set('api_key', 'supersecretapikey')
        config.set('debug', 'True')

        # Save the config
        config.save()
        assert os.path.exists(config_file), "Config file was not created."

        # Load the config in a new instance
        config2 = EncryptedConfig(key=b'secretkey123456789012', config_file=config_file)
        loaded = config2.load()
        assert loaded, "Failed to load config file."

        assert config2.get('database_url') == 'postgresql://user:pass@localhost/db'
        assert config2.get('api_key') == 'supersecretapikey'
        assert config2.get('debug') == 'True'
        print("  PASS: Encrypted config storage and retrieval work correctly.")


def test_tamper_detector():
    print("Testing TamperDetector...")
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a few test files
        file1 = os.path.join(tmpdir, 'file1.txt')
        file2 = os.path.join(tmpdir, 'file2.txt')
        with open(file1, 'w') as f:
            f.write('This is file 1.')
        with open(file2, 'w') as f:
            f.write('This is file 2.')

        detector = TamperDetector()
        detector.add_file(file1)
        detector.add_file(file2)

        # Save baseline
        baseline_file = os.path.join(tmpdir, 'baseline.json')
        assert detector.save_baseline(baseline_file), "Failed to save baseline."

        # Check integrity - should be OK
        is_tampered, tampered_files = detector.check_integrity()
        assert not is_tampered, f"False positive: {tampered_files}"
        print("  PASS: Integrity check passes on unchanged files.")

        # Tamper with a file
        with open(file1, 'w') as f:
            f.write('This is the tampered file 1.')

        is_tampered, tampered_files = detector.check_integrity()
        assert is_tampered, "Tampering not detected."
        assert file1 in tampered_files, f"Expected {file1} in tampered files, got {tampered_files}"
        print("  PASS: Tampering detected correctly.")

        # Remove a file
        os.remove(file2)
        is_tampered, tampered_files = detector.check_integrity()
        assert is_tampered, "File removal not detected."
        assert file2 in tampered_files, f"Expected {file2} in tampered files, got {tampered_files}"
        print("  PASS: File removal detected correctly.")


if __name__ == '__main__':
    test_obfuscator()
    test_encrypted_config()
    test_tamper_detector()
    print("\nAll tests passed!")
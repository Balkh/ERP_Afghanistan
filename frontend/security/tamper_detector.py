import hashlib
import os
import json


class TamperDetector:
    def __init__(self, baseline_file=None):
        """
        Initialize the TamperDetector.

        :param baseline_file: The file containing the baseline hashes of critical files.
                              If None, it defaults to 'baseline.json' in the current directory.
        """
        self.baseline_file = baseline_file or os.path.join(os.getcwd(), 'baseline.json')
        self.baseline = self._load_baseline()

    def _load_baseline(self):
        """
        Load the baseline hashes from the baseline file.

        :return: A dictionary mapping file paths to their expected hash values.
        """
        if not os.path.exists(self.baseline_file):
            return {}
        try:
            with open(self.baseline_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading baseline file: {e}")
            return {}

    def load_baseline(self, baseline_file):
        """
        Load baseline from a specific file.

        :param baseline_file: Path to the baseline file.
        :return: The baseline dictionary.
        """
        self.baseline_file = baseline_file
        self.baseline = self._load_baseline()
        return self.baseline

    def _calculate_hash(self, file_path):
        """
        Calculate the SHA256 hash of a file.

        :param file_path: The path to the file.
        :return: The hash as a hexadecimal string, or None if the file cannot be read.
        """
        try:
            with open(file_path, 'rb') as f:
                file_hash = hashlib.sha256()
                # Read the file in chunks to handle large files efficiently
                for chunk in iter(lambda: f.read(4096), b""):
                    file_hash.update(chunk)
                return file_hash.hexdigest()
        except Exception as e:
            print(f"Error calculating hash for {file_path}: {e}")
            return None

    def add_file(self, file_path):
        """
        Add a file to the baseline for tamper detection.

        :param file_path: The path to the file to add.
        :return: True if the file was added successfully, False otherwise.
        """
        if not os.path.exists(file_path):
            print(f"File not found: {file_path}")
            return False

        file_hash = self._calculate_hash(file_path)
        if file_hash is None:
            return False

        # Store the hash in the baseline dictionary
        self.baseline[file_path] = file_hash
        return True

    def save_baseline(self, file_path=None):
        """
        Save the current baseline to a file.

        :param file_path: The file path to save the baseline to. If None, uses the instance's baseline_file.
        :return: True if successful, False otherwise.
        """
        file_path = file_path or self.baseline_file
        try:
            with open(file_path, 'w') as f:
                json.dump(self.baseline, f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving baseline file: {e}")
            return False

    def check_integrity(self):
        """
        Check the integrity of all files in the baseline.

        :return: A tuple (is_tampered, tampered_files) where:
                 is_tampered is a boolean indicating if any file has been tampered with,
                 tampered_files is a list of file paths that have been tampered with or are missing.
        """
        tampered_files = []
        for file_path, expected_hash in self.baseline.items():
            if not os.path.exists(file_path):
                tampered_files.append(file_path)
                continue

            actual_hash = self._calculate_hash(file_path)
            if actual_hash is None:
                tampered_files.append(file_path)
                continue

            if actual_hash != expected_hash:
                tampered_files.append(file_path)

        is_tampered = len(tampered_files) > 0
        return is_tampered, tampered_files

    def get_baseline(self):
        """
        Get a copy of the current baseline.

        :return: A dictionary mapping file paths to their expected hash values.
        """
        return self.baseline.copy()


# Example usage and utility functions
def create_baseline_for_directory(directory, output_file=None, extensions=None):
    """
    Create a baseline for all files in a directory (and subdirectories) with given extensions.

    :param directory: The root directory to scan for files.
    :param output_file: The file to save the baseline to. If None, it will be saved as 'baseline.json' in the directory.
    :param extensions: A list of file extensions to include (e.g., ['.py', '.json']). If None, all files are included.
    :return: The TamperDetector instance with the baseline populated.
    """
    if output_file is None:
        output_file = os.path.join(directory, 'baseline.json')

    detector = TamperDetector(baseline_file=output_file)

    for root, dirs, files in os.walk(directory):
        for file in files:
            file_path = os.path.join(root, file)
            if extensions:
                if any(file.endswith(ext) for ext in extensions):
                    detector.add_file(file_path)
            else:
                detector.add_file(file_path)

    detector.save_baseline(output_file)
    return detector


if __name__ == "__main__":
    # Example usage: create a baseline for the current directory's Python files
    import sys
    if len(sys.argv) > 1:
        directory = sys.argv[1]
    else:
        directory = os.getcwd()

    print(f"Creating baseline for directory: {directory}")
    detector = create_baseline_for_directory(directory, extensions=['.py', '.json', '.txt'])
    print(f"Baseline created and saved to {detector.baseline_file}")

    # Example usage: check integrity
    is_tampered, tampered_files = detector.check_integrity()
    if is_tampered:
        print("Tampering detected!")
        for file in tampered_files:
            print(f"  - {file}")
    else:
        print("No tampering detected.")
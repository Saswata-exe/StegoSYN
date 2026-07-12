import pickle
import os
import pprint

def load_pickle(file_path):
    """Load a pickle file and return its content."""
    try:
        with open(file_path, "rb") as f:
            data = pickle.load(f)
        return data
    except FileNotFoundError:
        print(f"❌ File not found: {file_path}")
    except pickle.UnpicklingError:
        print(f"❌ Invalid pickle file (corrupted or not a pickle).")
    except PermissionError:
        print(f"❌ Permission denied: {file_path}")
    except Exception as e:
        print(f"❌ Error: {e}")
    return None

def print_full_data(data):
    """Print the full content of the loaded data."""
    print("\n--- Full Data Content ---")

    # Check if it's a pandas object
    try:
        import pandas as pd
        if isinstance(data, (pd.DataFrame, pd.Series)):
            # Show all rows and columns without truncation
            with pd.option_context('display.max_rows', None,
                                   'display.max_columns', None,
                                   'display.width', None,
                                   'display.max_colwidth', None):
                print(data)
            return
    except ImportError:
        pass  # pandas not installed

    # For built-in containers: use pprint for readability
    if isinstance(data, (dict, list, tuple, set)):
        pprint.pprint(data, indent=2, width=120, compact=False)
    else:
        # For other objects, just print the string representation
        print(data)

if __name__ == "__main__":
    print("📂 Pickle File Loader (Full Data)")
    print("Type 'exit' or 'quit' to stop.\n")

    while True:
        file_path = input("Enter the path to your .pkl file: ").strip()

        if file_path.lower() in ('exit', 'quit', ''):
            print("Goodbye!")
            break

        # Expand user home directory (e.g., ~/file.pkl)
        file_path = os.path.expanduser(file_path)

        data = load_pickle(file_path)
        if data is not None:
            print(f"✅ Loaded successfully from: {file_path}")
            print_full_data(data)

        print("\n" + "-" * 60 + "\n")

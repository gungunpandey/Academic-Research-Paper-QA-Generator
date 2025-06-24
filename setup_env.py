import os

def create_env_file():
    """
    Prompts the user for their Qdrant credentials and creates a .env file.
    """
    print("--- Qdrant Environment Setup ---")
    print("Please enter your Qdrant credentials.")

    qdrant_uri = input("Enter your QDRANT_URI: ").strip()
    qdrant_api_key = input("Enter your QDRANT_API_KEY: ").strip()

    # Get the directory of the current script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # Path for the new .env file
    env_path = os.path.join(script_dir, '.env')

    try:
        with open(env_path, 'w') as f:
            f.write(f'QDRANT_URI="{qdrant_uri}"\n')
            f.write(f'QDRANT_API_KEY="{qdrant_api_key}"\n')
        print(f"\nSuccessfully created .env file at: {env_path}")
        print("You can now run the other scripts.")
    except Exception as e:
        print(f"\nAn error occurred while creating the .env file: {e}")

if __name__ == "__main__":
    create_env_file() 
import json

class ConfigLoader:
    _instance = None
    _config = None

    def __new__(cls, config_file_path='config/ganglia_config.json'):
        if cls._instance is None:
            cls._instance = super(ConfigLoader, cls).__new__(cls)
            # Load the configuration as soon as the instance is created
            cls._config = cls.load_config(config_file_path)
            if cls._config is None:
                print("Configuration loading failed. Ensure the config file exists and is valid.")
        return cls._instance

    @classmethod
    def load_config(cls, config_file_path):
        try:
            with open(config_file_path, 'r') as file:
                print("Configuration loaded successfully.")
                return json.load(file)
        except FileNotFoundError:
            # Return an error message instead of logging
            error_msg = f"Config file not found at: {config_file_path}"
            print(error_msg)  # Optionally, you can still print, but caller should handle it
            return {"error": error_msg}
        except json.JSONDecodeError as e:
            # Return an error message instead of logging
            error_msg = f"Failed to parse config file: {e}"
            print(error_msg)  # Optionally, you can still print, but caller should handle it
            return {"error": error_msg}

    @classmethod
    def get_config(cls):
        if "error" in cls._config:
            raise Exception(cls._config["error"])  # Raising an exception if there was an error loading the config
        return cls._config

    @classmethod
    def get(cls, key):
        if cls._config is None:
            print("Configuration not loaded. Please ensure ConfigLoader is properly initialized.")
            return None
        # Recursive function to search through the config for the key
        def search_dict(sub_config, key):
            if key in sub_config:
                return sub_config[key]
            for k, v in sub_config.items():
                if isinstance(v, dict):
                    result = search_dict(v, key)
                    if result is not None:
                        return result
            return None

        result = search_dict(cls._config, key)
        if result is not None:
            return result
        else:
            error_msg = f"Key '{key}' not found in configuration."
            print(error_msg)  # Optionally, you can still print, but caller should handle it
            exit(1)


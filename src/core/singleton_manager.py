from src.core.radio_manager import RadioManager

class SingletonRadioManager:
    _instance = None

    @classmethod
    def get_instance(cls, status_update_callback=None):
        if cls._instance is None:
            cls._instance = RadioManager(status_update_callback=status_update_callback)
        return cls._instance
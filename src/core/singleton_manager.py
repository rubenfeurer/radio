import logging

from src.core.radio_manager import RadioManager

logger = logging.getLogger(__name__)


def singleton_with_callback(cls):
    """Decorator that creates a singleton instance of a class,
    allowing for callback initialization/updates.
    """
    instance = None

    def get_instance(status_update_callback=None):
        nonlocal instance
        if instance is None:
            logger.info(f"Creating new {cls.__name__} instance")
            instance = cls(status_update_callback=status_update_callback)
        elif status_update_callback is not None:
            logger.info(f"Updating {cls.__name__} callback")
            instance._status_update_callback = status_update_callback
        return instance

    # Add get_instance as a static method to the class
    cls.get_instance = staticmethod(get_instance)
    return cls


# Apply the decorator to RadioManager
@singleton_with_callback
class RadioManagerSingleton(RadioManager):
    pass

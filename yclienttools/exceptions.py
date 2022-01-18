class NotFoundException(Exception):
    '''Raised when no result was found when searching for a specific object.'''
    pass


class SizeNotSupportedException(Exception):
    '''Raised when an action cannot be performed due to size limitations in rules'''
    pass

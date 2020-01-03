from enum import Enum


class GroupByOption(Enum):
    none = 'none'
    resource = 'resource'
    location = 'location'

    def __str__(self):
        return self.name

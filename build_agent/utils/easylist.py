# Copyright (2025) Bytedance Ltd. and/or its affiliates 

# Licensed under the Apache License, Version 2.0 (the "License"); 
# you may not use this file except in compliance with the License. 
# You may obtain a copy of the License at 

#     https://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software 
# distributed under the License is distributed on an "AS IS" BASIS, 
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. 
# See the License for the specific language governing permissions and 
# limitations under the License. 


class EasyList:
    def __init__(self, initial_items=None):
        """Initialize a new EasyList, optionally with initial items"""
        self.items = initial_items if initial_items is not None else list()

    def add(self, item):
        """Add an element to the list"""
        self.items.append(item)

    def remove(self, item):
        """Remove an element from the list"""
        if item in self.items:
            self.items.remove(item)

    def get(self, index):
        """Get element at specified index"""
        if 0 <= index < len(self.items):
            return self.items[index]
        return None

    def size(self):
        """Return the size of the list"""
        return len(self.items)

    def clear(self):
        """Clear the list"""
        self.items = []

    def sort(self):
        """Sort the list"""
        self.items.sort()

    def reverse(self):
        """Reverse the order of elements in the list"""
        self.items.reverse()

    def contains(self, item):
        """Check if the list contains an item"""
        return item in self.items

    def extend(self, other):
        """Extend the list with elements from another list"""
        self.items.extend(other)

    def index_of(self, item):
        """Return the index of an item, -1 if not found"""
        try:
            return self.items.index(item)
        except ValueError:
            return -1

    def insert(self, index, item):
        """Insert a new element at specified index"""
        self.items.insert(index, item)

    def pop(self, index=-1):
        """Remove and return element at specified position, default last"""
        if 0 <= index < len(self.items):
            return self.items.pop(index)
        return None

    def replace(self, index, item):
        """Replace element at specified index if index is valid"""
        if 0 <= index < len(self.items):
            self.items[index] = item
        else:
            print("Index out of bounds") 

    def __str__(self):
        """Return string representation of the list"""
        return str(self.items)

from typing import Iterator

Cell = tuple[int, int]

class GridObject:
    """
    A grid-based object that is used in a Gridmap container. It has a convex rectangular shape. It can also occupy multiple cells.
    """
    def __init__(self, R: range, C: range) -> None:
        self._R, self._C = R, C

    @property
    def R(self): 
        """ Rows where object exists """
        return self._R
    @property
    def C(self): 
        """ Columns where object exists """
        return self._C
    @property
    def cells(self) -> Iterator[Cell]:
        """ Return cells relative to object where it exists. These are the intersection of R and C. """
        return ((r, c) for c in self.C for r in self.R)

class GridMap():
    """
    A standard grid class, ueful for grid-based object manipulation that allows empty cells.

    It includes list-inspired functions, slicing/scanning, and GridObject enumeration. 
    Rows and columns are 0-indexed from top to bottom and left to right, respectively.
    Empty cells are still part of the grid as long as they are within grid boundaries. 

    There can only be at most one grid object in each cell.
    """
    def __init__(self, rows: int, cols: int, width: int, height: int) -> None:
        self._rows = rows
        self._cols = cols
        self._width = width
        self._height = height
        self.clear()
    
    @property
    def rows(self): 
        """ Number of grid's rows """
        return self._rows
    @property
    def cols(self): 
        """ Number of grid's columns """
        return self._cols
    @property
    def width(self): return self._width
    @property
    def height(self): return self._height
    @property
    def table(self): 
        """ Table of object values of grid """
        return self._table
    @property
    def cellwidth(self) -> int: return self.width//self.cols
    @property
    def cellheight(self) -> int: return self.height//self.rows

    def __iter__(self) -> Iterator[GridObject]:
        """ Returns all objects in the grid """
        return self.scan(range(self.rows), range(self.cols))

    def __contains__(self, obj: GridObject) -> bool:
        try:
            self.find(obj)
        except ValueError:
            return False
        return True
    
    def enumerate(self) -> Iterator[tuple[Cell, GridObject]]:
        """ Enumerates all grid objects with their cell locations """
        enumerated: set[GridObject] = set()
        for r, row in enumerate(self.table):
            for c, obj in enumerate(row):
                if obj is not None and obj not in enumerated: 
                    enumerated.add(obj)
                    yield (r - min(obj.R), c - min(obj.C)), obj

    def clear(self):
        self._table: list[list[GridObject | None]] = [[None]*self.cols for _ in range(self.rows)]  
    
    def replace(self, r: int, c: int, obj: GridObject): 
        """ Place GridObject on grid """
        for dr, dc in obj.cells:
            if self._table[r + dr][c + dc] is not None: raise ValueError('Cannot place GridObject on occupied space!')
        for dr, dc in obj.cells:
            self._table[r + dr][c + dc] = obj
            
    def remove(self, obj: GridObject):
        """ Removes GridObject from grid """
        r, c = self.find(obj)
        for dr, dc in obj.cells:
            self._table[r + dr][c + dc] = None
    
    def pop(self, r: int, c: int) -> GridObject:
        """ Removes and returns grid object at cell """
        obj = self.table[r][c]
        if obj is None: raise ValueError('Cannot remove null GridObject from GridMap')
        self.remove(obj)
        return obj

    def move(self, obj: GridObject, r: int, c: int):
        """ Moves object from its previous position on the grid """
        self.remove(obj)
        self.replace(r, c, obj)
    
    def find(self, obj: GridObject) -> Cell:
        """ Finds the grid coords of the GridObject """
        for r in range(self.rows):
            for c in range(self.cols):
                if self.table[r][c] == obj: return r - min(obj.R), c - min(obj.C)
        raise ValueError('Gridmap does not have GridObject')    

    def scan(self, R: range, C: range) -> Iterator[GridObject]:
        """ Scans subgrid of cells and returns GridObjects within. Works like a 2D slicer """
        for r in R:
            for c in C:
                if 0 <= r < self.rows and 0 <= c < self.cols:
                    obj = self._table[r][c]
                    if obj is not None: yield obj
import os
from aiida.orm import Data
from netCDF4 import Dataset
import tempfile
from pathlib import Path

class NetcdfData(Data):

    def __init__(self, filepath, **kwargs):
        """
        Data plugin for Netcdf objects.
        """
        
        super().__init__(**kwargs)

        nc_file = Dataset(filepath, mode='r')

        filename = os.path.basename(filepath)  
        self.put_object_from_file(filepath, filename)    
        self._nc_file = nc_file
        self._set_attributes(nc_file, filename)

    def _set_attributes(self, nc_file, filename):

        g_att = {}
        for a in nc_file.ncattrs():
            g_att[a] = repr(nc_file.getncattr(a))

        self.base.attributes.set('global_attributes', g_att) 
        self.base.attributes.set('filename', filename)

    def _get_nc(self):
        filename = self.base.attributes.get('filename')
        with tempfile.TemporaryDirectory() as td:
            self.copy_tree(Path(td))
            nc_file = Dataset(Path(td)/filename, mode='r')
            return nc_file

    def _get_netcdf(self):
        return self._get_nc_from_repo()
    
    def p_ncdump(self):
        pass
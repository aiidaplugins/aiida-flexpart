import os
from aiida.orm import Data
from netCDF4 import Dataset
import tempfile
from pathlib import Path

class NetCDFData(Data):

    def __init__(self, filepath=None, remote_path=None, **kwargs):
        """
        Data plugin for Netcdf objects.
        """
        super().__init__(**kwargs)
        if filepath is not None:
            filename = os.path.basename(filepath)
            self.set_remote_path(remote_path)
            self.set_filename(filename)

            #open and read as NetCDF
            nc_file = Dataset(filepath, mode='r')
            self.set__global_attributes(nc_file)

            #put object in repo
            #self.put_object_from_file(filepath, filename)    

    def set_remote_path(self, val):
        self.base.attributes.set('remote_path', val)

    def get_remote_path(self) -> str:
        return self.base.attributes.get('remote_path')

    def set_filename(self, val):
        self.base.attributes.set('filename', val)

    def set__global_attributes(self, nc_file):

        g_att = {}
        for a in nc_file.ncattrs():
            g_att[a] = repr(nc_file.getncattr(a))
        self.base.attributes.set('global_attributes', g_att) 

        nc_dimensions = {i:len(nc_file.dimensions[i]) for i in nc_file.dimensions}
        self.base.attributes.set('dimensions', nc_dimensions)

    def ncdump(self):
        """
        Small python version of ncdump.
        """
        print("dimensions:")
        for k,v in self.base.attributes.get('dimensions').items():
            print('\t%s =' %k,v)

        print('// global attributes:')
        for k,v in self.base.attributes.get('global_attributes').items():
            print('\t:%s =' %k,v)
import os
from aiida.orm import RemoteData

class NetCdfData(RemoteData):

    def __init__(self, filepath=None, remote_path=None, **kwargs):
        """
        Data plugin for Netcdf files.
        """
        super().__init__(**kwargs)
        if filepath is not None:
            filename = os.path.basename(filepath)
            self.set_remote_path(remote_path)
            self.set_filename(filename)

            if ('g_att' in kwargs and 
               'nc_dimensions' in kwargs):
                self.set_global_attributes(kwargs['g_att'],
                                           kwargs['nc_dimensions'])

    def set_filename(self, val):
        self.base.attributes.set("filename", val)

    def set_global_attributes(self,g_att,nc_dimensions):
        self.base.attributes.set("global_attributes", g_att)
        self.base.attributes.set("dimensions", nc_dimensions)

    def ncdump(self):
        """Small python version of ncdump."""
        print("dimensions:")
        for k, v in self.base.attributes.get("dimensions").items():
            print(f"\t {k} = {v}")
        print("// global attributes:")
        for k, v in self.base.attributes.get("global_attributes").items():
            print(f"\t :{k} = {v}")
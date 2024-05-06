import os
from aiida.orm import RemoteData
from netCDF4 import Dataset

class NetCDFData(RemoteData):

    def __init__(self, filepath=None, remote_path=None, **kwargs):
        """
        Data plugin for Netcdf files.
        """
        super().__init__(**kwargs)
        if filepath is not None:
            filename = os.path.basename(filepath)
            self.set_remote_path(remote_path)
            self.set_filename(filename)

            # open and read as NetCDF
            nc_file = Dataset(filepath, mode="r")
            self.set_global_attributes(nc_file)

    def set_filename(self, val):
        self.base.attributes.set("filename", val)

    def set_global_attributes(self, nc_file):

        g_att = {}
        for a in nc_file.ncattrs():
            g_att[a] = repr(nc_file.getncattr(a))
        self.base.attributes.set("global_attributes", g_att)

        nc_dimensions = {i: len(nc_file.dimensions[i]) for i in nc_file.dimensions}
        self.base.attributes.set("dimensions", nc_dimensions)

    def ncdump(self):
        """
        Small python version of ncdump.
        """
        print("dimensions:")
        for k, v in self.base.attributes.get("dimensions").items():
            print("\t%s =" % k, v)

        print("// global attributes:")
        for k, v in self.base.attributes.get("global_attributes").items():
            print("\t:%s =" % k, v)
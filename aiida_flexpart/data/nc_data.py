import os
from aiida.orm import RemoteData


class NetCdfData(RemoteData):

    def __init__(
        self, filepath=None, remote_path=None, g_att=None, nc_dimensions=None, **kwargs
    ):
        """
        Data plugin for Netcdf files.
        """
        super(NetCdfData,self).__init__()
        if filepath is not None:
            filename = os.path.basename(filepath)
            self.set_remote_path(remote_path)
            self.set_filename(filename)
            self.set_global_attributes(g_att, nc_dimensions)
        if kwargs:
            for k,v in kwargs.items():
                self.base.attributes.set(k, v)


    def set_filename(self, val):
        self.base.attributes.set("filename", val)

    def set_global_attributes(self, g_att, nc_dimensions):
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

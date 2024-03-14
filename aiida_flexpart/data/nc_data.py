import os
from aiida.orm import Data
from netCDF4 import Dataset


class NetCDFData(Data):

    def __init__(self, filepath, **kwargs):
        super().__init__(**kwargs)

        filename = os.path.basename(filepath)  # Get the filename from the absolute path
        self.put_object_from_file(filepath, filename)  # Store the file in the repository under the given filename
        self.base.attributes.set('filename', filename)  # Store in the attributes what the filename is

    def get_content(self):
        filename = self.base.attributes.get('filename')
        return self.get_object_content(filename)
    
    def get_info(self):
        data_nest = Dataset(self.base.attributes.get('filename'), mode='r')
        #spec = data_nest.variables['spec001'][:].data
        
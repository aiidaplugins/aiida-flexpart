import os
from aiida.orm import Data
from netCDF4 import Dataset

def ncdump(nc_fid, verb=True):
    '''
    ncdump outputs dimensions, variables and their attribute information.
    The information is similar to that of NCAR's ncdump utility.
    ncdump requires a valid instance of Dataset.

    Parameters
    ----------
    nc_fid : netCDF4.Dataset
        A netCDF4 dateset object
    verb : Boolean
        whether or not nc_attrs, nc_dims, and nc_vars are printed

    Returns
    -------
    nc_attrs : list
        A Python list of the NetCDF file global attributes
    nc_dims : list
        A Python list of the NetCDF file dimensions
    nc_vars : list
        A Python list of the NetCDF file variables
    '''
    def print_ncattr(key):
        """
        Prints the NetCDF file attributes for a given key

        Parameters
        ----------
        key : unicode
            a valid netCDF4.Dataset.variables key
        """
        try:
            print("\t\ttype:", repr(nc_fid.variables[key].dtype))
            for ncattr in nc_fid.variables[key].ncattrs():
                print('\t\t%s:' % ncattr,\
                      repr(nc_fid.variables[key].getncattr(ncattr)))
        except KeyError:
            print("\t\tWARNING: %s does not contain variable attributes" % key)

    # NetCDF global attributes
    nc_attrs = nc_fid.ncattrs()
    if verb:
        print ("Global Attributes:")
        for nc_attr in nc_attrs:
            print('\t%s:' % nc_attr, repr(nc_fid.getncattr(nc_attr)))
    nc_dims = [dim for dim in nc_fid.dimensions]  # list of nc dimensions
    # Dimension shape information.
    if verb:
        print("dimension information:")
        for dim in nc_dims:
            print(dim)
            print("\t\tsize:", len(nc_fid.dimensions[dim]))
            print_ncattr(dim)
    # Variable information.
    nc_vars = [var for var in nc_fid.variables]  # list of nc variables
    if verb:
        print("variable information:")
        for var in nc_vars:
            if var not in nc_dims:
                print(var)
                print("\t\tdimensions:", nc_fid.variables[var].dimensions)
                print("\t\tsize:", nc_fid.variables[var].size)
                print_ncattr(var)
    return nc_attrs, nc_dims, nc_vars


class NetCDFData(Data):

    def __init__(self, filepath, **kwargs):
        """
        Data plugin for Netcdf files.
        """

        nc_file = Dataset(filepath, mode='r')
        
        super().__init__(**kwargs)

        filename = os.path.basename(filepath)  
        self.put_object_from_file(filepath, filename)  
        self.base.attributes.set('filename', filename)  
        self.nc_file = nc_file

        att_dict = {}
        for a in nc_file.ncattrs():
            att_dict[a] = repr(nc_file.getncattr(a))

        self.base.attributes.set('global_attributes', att_dict) 

    def get_info(self):
        """ 
        Print netcdf info in a similar format as ncdump -h
        """
        ncdump(self.nc_file)  
    
    def get_netcdf(self):
        """
        Get NetCDF file associated with this node.
        """
        return self.nc_file
       
        
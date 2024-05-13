from aiida.engine import WorkChain, calcfunction
from aiida.plugins import DataFactory
from aiida import orm
from pathlib import Path
import tempfile

NetCDF = DataFactory("netcdf.data")

def check(nc_file,version):
    """
    Checks if there is a netcdf file stored with the same name,
    if so, it checks the created date, if that is a match then returns
    False.
    """
    qb = orm.QueryBuilder()
    qb.append(
            NetCDF,
            project=[f"attributes.global_attributes.{version}"],
            filters={"attributes.filename": nc_file.attributes['filename']},
            )
    if qb.all():
        for i in qb.all():
            if i[0] == nc_file.attributes['global_attributes'][version]:
                return False
    return True

def validate_version(nc_file):
    if 'history' in nc_file.attributes['global_attributes'].keys():
        return 'history'
    elif 'created' in nc_file.attributes['global_attributes'].keys():
        return 'created'
    return None
    
@calcfunction
def store(i,folder):
    with tempfile.TemporaryDirectory() as td:
        folder.getfile(Path(folder.get_remote_path())/i.value, Path(td)/i.value)
        node = NetCDF(str(Path(td)/i.value),
                        remote_path = str(Path(folder.get_remote_path())),
                        computer = folder.computer
                     )
        
        if validate_version(node) == None:
            return  
        elif check(node,validate_version(node)):
            return node
        return
        
class InspectWorkflow(WorkChain):
    @classmethod
    def define(cls, spec):
        super().define(spec)
        spec.input_namespace('remotes',valid_type=orm.RemoteData,required=False)
        spec.input_namespace('remotes_cs',valid_type=orm.RemoteStashFolderData,required=False)
        spec.outputs.dynamic = True
        spec.outline(
            cls.fill_remote_data,
            cls.inspect,
            cls.results,
        )

    def fill_remote_data(self):
        self.ctx.dict_remote_data = {}
        if 'remotes' in self.inputs:
            self.ctx.dict_remote_data = self.inputs.remotes
        else:
            for k,v in self.inputs.remotes_cs.items():
                self.ctx.dict_remote_data[k] = orm.RemoteData(remote_path = v.target_basepath,
                                                computer = v.computer
                                                )
    def inspect(self):
        self.ctx.list_files = []
        for v in self.ctx.dict_remote_data.values():
                for i in v.listdir():
                    if '.nc' in i:
                        self.ctx.list_files.append(i)
                        store(i,v)
                    
    def results(self):
        self.out('result', self.ctx.list_files)
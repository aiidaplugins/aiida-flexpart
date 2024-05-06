from aiida.engine import WorkChain, calcfunction
from aiida.plugins import DataFactory
from aiida import orm
from pathlib import Path
import tempfile

NetCDF = DataFactory("netcdf.data")

def check(nc_file):
    """
    Checks if there is a netcdf file stored with the same name,
    if so, it checks the created date, if that is a match then returns
    False.
    """
    qb = orm.QueryBuilder()
    qb.append(
            NetCDF,
            project=["attributes.global_attributes.created"],
            filters={"attributes.filename": nc_file.attributes['filename']},
            )
    if qb.all():
        for i in qb.all():
            if i[0] == nc_file.attributes['global_attributes']['created']:
                return False
    return True
    
@calcfunction
def store(i,folder):
    with tempfile.TemporaryDirectory() as td:
        folder.getfile(Path(folder.get_remote_path())/i.value, Path(td)/i.value)
        node = NetCDF(str(Path(td)/i.value),
                        remote_path = str(Path(folder.get_remote_path())),
                        computer = folder.computer
                     )
        if check(node):
            return node
        return
        
class InspectWorkflow(WorkChain):
    @classmethod
    def define(cls, spec):
        super().define(spec)
        spec.input_namespace('remotes',valid_type=orm.RemoteData,required=False)
        spec.outputs.dynamic = True
        spec.outline(
            cls.inspect,
            cls.results,
        )

    def inspect(self):
        self.ctx.list_files = []
        for v in self.inputs.remotes.values():
                for i in v.listdir():
                    if '.nc' in i:
                        self.ctx.list_files.append(i)
                        store(i,v)
                    
    def results(self):
        self.out('result', self.ctx.list_files)
from aiida.engine import WorkChain, calcfunction
from aiida.plugins import DataFactory
from aiida import orm
from pathlib import Path
import tempfile

NetCDF = DataFactory("netcdf.data")

def check(nc_file):
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
        spec.input('remotes',valid_type=orm.RemoteData,required=False)
        spec.input_namespace('remotes_cs', valid_type=orm.RemoteStashFolderData, required=False)
        spec.outputs.dynamic = True
        spec.outline(
            cls.inspect,
            cls.save_file,
            cls.results,
        )

    def inspect(self):
        self.ctx.list_files = [] 
        if 'remotes' in self.inputs:
            for i in self.inputs.remotes.listdir()[:10]:
                if '.nc' in i:
                    self.ctx.list_files.append(i)
                
    def save_file(self):
        for i in self.ctx.list_files:
            self.report(f'processing {i}')
            store(i,self.inputs.remotes)

    def results(self):
        self.out('result', self.ctx.list_files)
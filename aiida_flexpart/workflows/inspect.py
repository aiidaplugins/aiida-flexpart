from aiida.engine import WorkChain, calcfunction
from aiida.plugins import DataFactory
from aiida import orm
from pathlib import Path
import tempfile
from netCDF4 import Dataset

NetCDF = DataFactory("netcdf.data")


def check(nc_file, version):
    """
    Checks if there is a netcdf file stored with the same name,
    if so, it checks the created date, if that is a match then returns
    False.
    """
    qb = orm.QueryBuilder()
    qb.append(
        NetCDF,
        project=[f"attributes.global_attributes.{version}"],
        filters={"attributes.filename": nc_file.attributes["filename"]},
    )
    if qb.all():
        for i in qb.all():
            if i[0] == nc_file.attributes["global_attributes"][version]:
                return False
    return True

@calcfunction
def store(remote_dir, file, time_label, nc_type):
    with tempfile.TemporaryDirectory() as td:
        remote_path = Path(remote_dir.get_remote_path()) / file.value
        temp_path = Path(td) / file.value
        remote_dir.getfile(remote_path, temp_path)

        # fill global attributes and dimensions
        nc_file = Dataset(str(temp_path), mode="r")
        nc_dimensions = {i: len(nc_file.dimensions[i]) for i in nc_file.dimensions}
        global_att = {}
        for a in nc_file.ncattrs():
            global_att[a] = repr(nc_file.getncattr(a))

        node = NetCDF(
            str(temp_path),
            remote_path=str(remote_path),
            computer=remote_dir.computer,
            g_att=global_att,
            nc_dimensions=nc_dimensions,
            other = {
                    'time_label' : time_label.value,
                    'nc_type' : nc_type.value
                    }
        )

        if "history" in node.attributes["global_attributes"].keys():
            if check(node, "history"):
                return node
        elif "created" in node.attributes["global_attributes"].keys():
            if check(node, "created"):
                return node
        else:
            return
        



class InspectWorkflow(WorkChain):
    @classmethod
    def define(cls, spec):
        super().define(spec)
        spec.input_namespace("remotes", valid_type=orm.RemoteData, required=False)
        spec.input_namespace(
            "remotes_cs", valid_type=orm.RemoteStashFolderData, required=False
        )
        spec.input('time_label', valid_type=orm.Str, required=False)
        spec.input('nc_type', valid_type=orm.Str, required=False)
        spec.outputs.dynamic = True
        spec.outline(
            cls.fill_remote_data,
            cls.inspect,
        )
    def fill_remote_data(self):
        self.ctx.dict_remote_data = {}
        if "remotes" in self.inputs:
            self.ctx.dict_remote_data = self.inputs.remotes
        else:
            for k, v in self.inputs.remotes_cs.items():
                self.ctx.dict_remote_data[k] = orm.RemoteData(
                    remote_path=v.target_basepath, computer=v.computer
                )

    def inspect(self):
        for _, i in self.ctx.dict_remote_data.items():
            for file in i.listdir():
                if ".nc" in file:
                    store(i, file, self.inputs.time_label, self.inputs.nc_type)

# -*- coding: utf-8 -*-
from aiida import engine, orm
from aiida_shell import launch_shell_job
from aiida_flexpart.utils import get_simulation_period

#possible models
cosmo_models = ['cosmo7', 'cosmo1', 'kenda1']
ECMWF_models = ['IFS_GL_05', 'IFS_GL_1', 'IFS_EU_02', 'IFS_EU_01']


class TransferMeteoWorkflow(engine.WorkChain):
    """Multi-dates workflow for transfering the necessary
    Meteorological data for the subsequent Flexpart
    simulations."""
    @classmethod
    def define(cls, spec):
        """Specify inputs and outputs."""
        super().define(spec)

        spec.input('check_meteo_cosmo_code', valid_type=orm.AbstractCode)
        spec.input('check_meteo_ifs_code', valid_type=orm.AbstractCode)

        spec.input('simulation_dates', valid_type=orm.List, required=False)
        spec.input('gribdir', valid_type=orm.Str, required=True)

        spec.input('model', valid_type=orm.List, required=True)
        spec.input('model_offline', valid_type=orm.List, required=True)
        spec.input('offline_integration_time', valid_type=orm.Int)
        spec.input('integration_time', valid_type=orm.Int)
        spec.input('command', valid_type=orm.Dict)

        spec.outline(
            cls.setup,
            engine.while_(cls.date)(cls.prepare_meteo_folder,
                                    engine.if_(cls.offline)(
                                        cls.prepare_meteo_folder),
                                    cls.add_index))

    def setup(self):
        self.ctx.index = 0

    def date(self):
        self.ctx.offline = False
        return self.ctx.index < len(self.inputs.simulation_dates)

    def offline(self):
        if self.inputs.offline_integration_time > 0:
            self.ctx.offline = True
            return True
        return False

    def add_index(self):
        self.ctx.index += 1

    def prepare_meteo_folder(self):
        model_list = self.inputs.model
        code_ = self.inputs.check_meteo_cosmo_code
        age_class_ = self.inputs.integration_time.value * 3600

        if all(mod in ECMWF_models
               for mod in self.inputs.model) and self.inputs.model:
            code_ = self.inputs.check_meteo_ifs_code

        if self.ctx.offline > 0:
            age_class_ = self.inputs.offline_integration_time.value * 3600
            model_list = self.inputs.model_offline
            code_ = self.inputs.check_meteo_ifs_code

        e_date, s_date = get_simulation_period(
            self.inputs.simulation_dates[self.ctx.index],
            age_class_,
            self.inputs.command.get_dict()['release_duration'],
            self.inputs.command.get_dict()['simulation_direction'],
        )
        self.report(f'preparing meteo from {s_date} to {e_date}')

        node_list = []
        for mod in model_list:
            self.report(f'transfering {mod} meteo')
            _, node = launch_shell_job(
                code_,
                arguments=' -s {sdate} -e {edate} -g {gribdir} -m {model} -a',
                nodes={
                    'sdate': orm.Str(s_date),
                    'edate': orm.Str(e_date),
                    'gribdir': self.inputs.gribdir,
                    'model': orm.Str(mod),
                },
            )
            node_list.append(node)

        if all(node.is_finished_ok for node in node_list):
            self.report('ALL meteo OK')

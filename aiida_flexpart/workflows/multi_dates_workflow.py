# -*- coding: utf-8 -*-
"""Flexpart multi-dates WorkChain."""
from aiida import engine, plugins, orm
from aiida_shell import launch_shell_job
from aiida_flexpart.utils import get_simulation_period

#plugins
FlexpartCosmoCalculation = plugins.CalculationFactory('flexpart.cosmo')
FlexpartIfsCalculation = plugins.CalculationFactory('flexpart.ifs')
FlexpartPostCalculation = plugins.CalculationFactory('flexpart.post')

#possible models
cosmo_models = ['cosmo7', 'cosmo1', 'kenda1']
ECMWF_models = ['IFS_GL_05', 'IFS_GL_1', 'IFS_EU_02', 'IFS_EU_01']


class FlexpartMultipleDatesWorkflow(engine.WorkChain):
    """Flexpart multi-dates workflow"""
    @classmethod
    def define(cls, spec):
        """Specify inputs and outputs."""
        super().define(spec)

        #codes
        spec.input('fcosmo_code', valid_type=orm.AbstractCode)
        spec.input('check_meteo_cosmo_code', valid_type=orm.AbstractCode)
        spec.input('fifs_code', valid_type=orm.AbstractCode)
        spec.input('check_meteo_ifs_code', valid_type=orm.AbstractCode)
        spec.input('post_processing_code', valid_type=orm.AbstractCode)

        # Basic Inputs
        spec.input('simulation_dates',
                   valid_type=orm.List,
                   help='A list of the starting dates of the simulations')
        spec.input('model', valid_type=orm.List, required=True)
        spec.input('model_offline', valid_type=orm.List, required=True)
        spec.input('offline_integration_time', valid_type=orm.Int)
        spec.input('integration_time',
                   valid_type=orm.Int,
                   help='Integration time in hours')
        spec.input(
            'parent_calc_folder',
            valid_type=orm.RemoteData,
            required=False,
            help=
            'Working directory of a previously ran calculation to restart from.'
        )

        #model settings
        spec.input('input_phy', valid_type=orm.Dict)
        spec.input('command', valid_type=orm.Dict)
        spec.input('release_settings', valid_type=orm.Dict)
        spec.input('locations',
                   valid_type=orm.Dict,
                   help='Dictionary of locations properties.')

        #meteo related inputs
        spec.input('meteo_inputs',
                   valid_type=orm.Dict,
                   required=False,
                   help='Meteo models input params.')
        spec.input('meteo_inputs_offline',
                   valid_type=orm.Dict,
                   required=False,
                   help='Meteo models input params.')
        spec.input(
            'meteo_path',
            valid_type=orm.List,
            required=False,
            help='Path to the folder containing the meteorological input data.'
        )
        spec.input(
            'meteo_path_offline',
            valid_type=orm.List,
            required=False,
            help='Path to the folder containing the meteorological input data.'
        )
        spec.input('gribdir', valid_type=orm.Str, required=True)

        #others
        spec.input('outgrid', valid_type=orm.Dict)
        spec.input('outgrid_nest', valid_type=orm.Dict, required=False)
        spec.input('species', valid_type=orm.RemoteData, required=True)
        spec.input_namespace('land_use',
                             valid_type=orm.RemoteData,
                             required=False,
                             dynamic=True,
                             help='#TODO')
        spec.input_namespace('land_use_ifs',
                             valid_type=orm.RemoteData,
                             required=False,
                             dynamic=True)

        spec.expose_inputs(FlexpartCosmoCalculation,
                           include=['metadata.options'],
                           namespace='flexpartcosmo')
        spec.expose_inputs(FlexpartIfsCalculation,
                           include=['metadata.options'],
                           namespace='flexpartifs')
        spec.expose_inputs(FlexpartPostCalculation,
                           include=['metadata.options'],
                           namespace='flexpartpost')

        # Outputs
        #spec.output('output_file', valid_type=orm.SinglefileData)
        spec.outputs.dynamic = True
        # What the workflow will do, step-by-step
        spec.outline(
            cls.setup,
            engine.while_(cls.condition)(
                engine.if_(cls.run_cosmo)(engine.if_(
                    cls.prepare_meteo_folder_cosmo)(cls.run_cosmo_simulation)),
                engine.if_(cls.run_ifs)(engine.if_(
                    cls.prepare_meteo_folder_ifs)(cls.run_ifs_simulation)),
                cls.post_processing,
            ),
            cls.results,
        )

    def condition(self):
        """multi dates loop"""
        return self.ctx.index < len(self.ctx.simulation_dates)

    def run_cosmo(self):
        """run cosmo simulation"""
        if all(mod in cosmo_models
               for mod in self.inputs.model) and self.inputs.model:
            return True
        return False

    def run_ifs(self):
        """run ifs simulation"""
        if (all(mod in ECMWF_models for mod in self.inputs.model)
                or all(mod in ECMWF_models
                       for mod in self.inputs.model_offline)
                and self.inputs.model and self.inputs.model_offline):
            return True
        return False

    def setup(self):
        """Prepare a simulation."""

        self.report('starting setup')

        self.ctx.index = 0
        self.ctx.simulation_dates = self.inputs.simulation_dates
        self.ctx.integration_time = self.inputs.integration_time
        self.ctx.offline_integration_time = self.inputs.offline_integration_time

        #model settings
        self.ctx.release_settings = self.inputs.release_settings
        self.ctx.command = self.inputs.command
        self.ctx.input_phy = self.inputs.input_phy
        self.ctx.locations = self.inputs.locations

        #others
        self.ctx.outgrid = self.inputs.outgrid
        self.ctx.species = self.inputs.species
        self.ctx.land_use = self.inputs.land_use
        #self.base.extras.set('this',3)

    def prepare_meteo_folder_ifs(self):
        """prepare meteo folder"""
        age_class_ = self.inputs.integration_time.value * 3600
        if self.ctx.offline_integration_time > 0:
            age_class_ = self.inputs.offline_integration_time.value * 3600
        e_date, s_date = get_simulation_period(
            self.ctx.simulation_dates[self.ctx.index], age_class_,
            self.ctx.command.get_dict()['release_duration'],
            self.ctx.command.get_dict()['simulation_direction'])

        self.report(f'preparing meteo from {s_date} to {e_date}')

        if all(mod in ECMWF_models
               for mod in self.inputs.model) and self.inputs.model:
            model_list = self.inputs.model
        else:
            model_list = self.inputs.model_offline

        node_list = []
        for mod in model_list:
            self.report(f'transfering {mod} meteo')
            _, node = launch_shell_job(
                self.inputs.check_meteo_ifs_code,
                arguments=' -s {sdate} -e {edate} -g {gribdir} -m {model} -a',
                nodes={
                    'sdate': orm.Str(s_date),
                    'edate': orm.Str(e_date),
                    'gribdir': self.inputs.gribdir,
                    'model': orm.Str(mod)
                })
            node_list.append(node)

        if all(node.is_finished_ok for node in node_list):
            self.report('ALL meteo OK')
            return True

        self.report('FAILED to transfer meteo')
        self.ctx.index += 1
        return False

    def prepare_meteo_folder_cosmo(self):
        """prepare meteo folder"""
        e_date, s_date = get_simulation_period(
            self.ctx.simulation_dates[self.ctx.index],
            self.inputs.integration_time.value * 3600,
            self.ctx.command.get_dict()['release_duration'],
            self.ctx.command.get_dict()['simulation_direction'])

        self.report(f'preparing meteo from {s_date} to {e_date}')

        node_list = []
        for mod in self.inputs.model:
            self.report(f'transfering {mod} meteo')
            _, node = launch_shell_job(
                self.inputs.check_meteo_cosmo_code,
                arguments=' -s {sdate} -e {edate} -g {gribdir} -m {model} -a',
                nodes={
                    'sdate': orm.Str(s_date),
                    'edate': orm.Str(e_date),
                    'gribdir': self.inputs.gribdir,
                    'model': orm.Str(mod)
                })
            node_list.append(node)

        if all(node.is_finished_ok for node in node_list):
            self.report('ALL meteo OK')
            return True

        self.report('FAILED to transfer meteo')
        self.ctx.index += 1
        return False

    def post_processing(self):
        """post processing"""
        self.report('starting post-processsing')
        builder = FlexpartPostCalculation.get_builder()
        builder.code = self.inputs.post_processing_code
        builder.input_dir = self.ctx.calculations[-1].outputs.remote_folder

        if self.ctx.offline_integration_time > 0:
            self.report(
                f'main: {self.ctx.calculations[-2].outputs.remote_folder}')
            self.report(
                f'offline: {self.ctx.calculations[-1].outputs.remote_folder}')
            builder.input_dir = self.ctx.calculations[-2].outputs.remote_folder
            builder.input_offline_dir = self.ctx.calculations[
                -1].outputs.remote_folder

        builder.metadata.options = self.inputs.flexpartpost.metadata.options

        running = self.submit(builder)
        self.to_context(calculations=engine.append_(running))

    def run_cosmo_simulation(self):
        """Run calculations for equation of state."""

        self.report(
            f'starting flexpart cosmo {self.ctx.simulation_dates[self.ctx.index]}'
        )

        builder = FlexpartCosmoCalculation.get_builder()
        builder.code = self.inputs.fcosmo_code

        #update command file
        new_dict = self.ctx.command.get_dict()
        new_dict['simulation_date'] = self.ctx.simulation_dates[self.ctx.index]
        new_dict['age_class'] = self.inputs.integration_time * 3600
        new_dict.update(self.inputs.meteo_inputs)

        #model settings
        builder.model_settings = {
            'release_settings': self.ctx.release_settings,
            'locations': self.ctx.locations,
            'command': orm.Dict(dict=new_dict),
            'input_phy': self.ctx.input_phy,
        }

        builder.outgrid = self.ctx.outgrid
        if 'outgrid_nest' in self.inputs:
            builder.outgrid_nest = self.inputs.outgrid_nest
        builder.species = self.ctx.species
        builder.land_use = self.ctx.land_use
        builder.meteo_path = self.inputs.meteo_path

        # Walltime, memory, and resources.
        builder.metadata.description = 'Test workflow to submit a flexpart calculation'
        builder.metadata.options = self.inputs.flexpartcosmo.metadata.options

        # Ask the workflow to continue when the results are ready and store them in the context
        running = self.submit(builder)
        self.to_context(calculations=engine.append_(running))
        if self.ctx.offline_integration_time == 0:
            self.ctx.index += 1

    def run_ifs_simulation(self):
        """Run calculations for equation of state."""
        # Set up calculation.
        self.report(
            f'running flexpart ifs for {self.ctx.simulation_dates[self.ctx.index]}'
        )
        builder = FlexpartIfsCalculation.get_builder()
        builder.code = self.inputs.fifs_code

        #changes in the command file
        new_dict = self.ctx.command.get_dict()
        new_dict['simulation_date'] = self.ctx.simulation_dates[self.ctx.index]

        if self.ctx.offline_integration_time > 0:
            new_dict['age_class'] = self.ctx.offline_integration_time * 3600
            new_dict['dumped_particle_data'] = True

            self.ctx.parent_calc_folder = self.ctx.calculations[
                -1].outputs.remote_folder
            builder.parent_calc_folder = self.ctx.parent_calc_folder
            self.report(f'starting from: {self.ctx.parent_calc_folder}')

            builder.meteo_path = self.inputs.meteo_path_offline
            new_dict.update(self.inputs.meteo_inputs_offline)

        else:
            new_dict['age_class'] = self.inputs.integration_time * 3600
            builder.meteo_path = self.inputs.meteo_path
            new_dict.update(self.inputs.meteo_inputs)

        #model settings
        builder.model_settings = {
            'release_settings': self.ctx.release_settings,
            'locations': self.ctx.locations,
            'command': orm.Dict(dict=new_dict),
        }

        builder.outgrid = self.ctx.outgrid
        if 'outgrid_nest' in self.inputs:
            builder.outgrid_nest = self.inputs.outgrid_nest
        builder.species = self.ctx.species
        builder.land_use = self.inputs.land_use_ifs

        # Walltime, memory, and resources.
        builder.metadata.description = 'Test workflow to submit a flexpart calculation'
        builder.metadata.options = self.inputs.flexpartifs.metadata.options

        # Ask the workflow to continue when the results are ready and store them in the context
        running = self.submit(builder)
        self.to_context(calculations=engine.append_(running))

        self.ctx.index += 1

    def results(self):
        """Process results."""
        for indx, calculation in enumerate(self.ctx.calculations):
            self.out(f'calculation_{indx}_output_file',
                     calculation.outputs.output_file)

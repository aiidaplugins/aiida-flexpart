# -*- coding: utf-8 -*-
"""Flexpart multi-dates WorkChain."""
from aiida import engine, plugins, orm
from aiida_flexpart.workflows.child_meteo_workflow import TransferMeteoWorkflow

# plugins
FlexpartCosmoCalculation = plugins.CalculationFactory("flexpart.cosmo")
FlexpartIfsCalculation = plugins.CalculationFactory("flexpart.ifs")
FlexpartPostCalculation = plugins.CalculationFactory("flexpart.post")

# possible models
cosmo_models = ["cosmo7", "cosmo1", "kenda1"]
ECMWF_models = ["IFS_GL_05", "IFS_GL_1", "IFS_EU_02", "IFS_EU_01"]


class FlexpartSimWorkflow(engine.WorkChain):
    """Flexpart multi-dates workflow"""

    @classmethod
    def define(cls, spec):
        """Specify inputs and outputs."""
        super().define(spec)

        # Codes
        spec.input("fcosmo_code", valid_type=orm.AbstractCode)
        spec.input("fifs_code", valid_type=orm.AbstractCode)
        spec.input("post_processing_code", valid_type=orm.AbstractCode)

        #extras
        spec.input('name', valid_type=str, non_db=True, required=False)

        # Basic Inputs
        spec.expose_inputs(TransferMeteoWorkflow)
        spec.input("date", valid_type=orm.Int, required=False)

        # Model settings
        # Command is exposed form TransferMeteoWorkflow
        spec.input("input_phy", valid_type=orm.Dict)
        spec.input("release_settings", valid_type=orm.Dict)
        spec.input("locations", valid_type=orm.Dict, 
                   help="Dictionary of locations properties."
        )

        # Meteo related inputs
        spec.input(
            "meteo_inputs",
            valid_type=orm.Dict,
            required=False,
            help="Meteo models input params.",
        )
        spec.input(
            "meteo_inputs_offline",
            valid_type=orm.Dict,
            required=False,
            help="Meteo models input params.",
        )
        spec.input(
            "meteo_path",
            valid_type=orm.List,
            required=False,
            help="Path to the folder containing the meteorological input data.",
        )
        spec.input(
            "meteo_path_offline",
            valid_type=orm.List,
            required=False,
            help="Path to the folder containing the meteorological input data.",
        )

        # Others
        spec.input("outgrid", valid_type=orm.Dict)
        spec.input("outgrid_nest", valid_type=orm.Dict, required=False)
        spec.input("species", valid_type=orm.RemoteData, required=True)
        spec.input_namespace(
            "land_use",
            valid_type=orm.RemoteData,
            required=False,
            dynamic=True,
            help="#TODO",
        )
        spec.input_namespace(
            "land_use_ifs", valid_type=orm.RemoteData, required=False, dynamic=True
        )
        spec.expose_inputs(
            FlexpartCosmoCalculation,
            include=["metadata.options"],
            namespace="flexpartcosmo",
        )
        spec.expose_inputs(
            FlexpartIfsCalculation,
            include=["metadata.options"],
            namespace="flexpartifs",
        )
        spec.expose_inputs(
            FlexpartPostCalculation,
            include=["metadata.options"],
            namespace="flexpartpost",
        )
        spec.outputs.dynamic = True

        #exit codes
        spec.exit_code(400, 'ERROR_CALCULATION_FAILED', 
                       'the previous calculation did not finish successfully')

        spec.outline(
            cls.setup,

            engine.if_(cls.run_cosmo)(
                cls.run_cosmo_simulation,
                cls.inspect_calculation
                ),
            engine.if_(cls.run_ifs)(
                cls.run_ifs_simulation,
                cls.inspect_calculation
                ),

            cls.post_processing,
            cls.results,
        )

    def run_cosmo(self):
        """run cosmo simulation"""
        if all(mod in cosmo_models for mod in self.inputs.model) and self.inputs.model:
            return True
        return False

    def run_ifs(self):
        """run ifs simulation"""
        if (
            all(mod in ECMWF_models for mod in self.inputs.model)
            or all(mod in ECMWF_models for mod in self.inputs.model_offline)
            and self.inputs.model
            and self.inputs.model_offline
        ):
            return True
        return False
    
    def inspect_calculation(self):
        if not self.ctx.calculations[-1].is_finished_ok:
            self.report('ERROR calculation did not finish ok')
            return self.exit_codes.ERROR_CALCULATION_FAILED
        self.report('calculation successfull')

    def setup(self):

        self.ctx.simulation_date = self.inputs.simulation_dates[self.inputs.date.value]
        self.ctx.integration_time = self.inputs.integration_time
        self.ctx.offline_integration_time = self.inputs.offline_integration_time

        # model settings
        self.ctx.release_settings = self.inputs.release_settings
        self.ctx.command = self.inputs.command
        self.ctx.input_phy = self.inputs.input_phy
        self.ctx.locations = self.inputs.locations

        # others
        self.ctx.outgrid = self.inputs.outgrid
        self.ctx.species = self.inputs.species
        self.ctx.land_use = self.inputs.land_use
        if 'name' in self.inputs:
            out_n = 'None'
            if 'outgrid_nest' in self.inputs:
                out_n = self.inputs.outgrid_nest.get_dict()
            self.node.base.extras.set(
                self.inputs.name, {
                    'command': self.ctx.command.get_dict(),
                    'input_phy': self.ctx.input_phy.get_dict(),
                    'release': self.ctx.release_settings.get_dict(),
                    'locations': self.ctx.locations.get_dict(),
                    'integration_time': self.ctx.integration_time.value,
                    'offline_integration_time':
                    self.ctx.offline_integration_time.value,
                    'model': self.inputs.model,
                    'model_offline': self.inputs.model_offline,
                    'outgrid': self.inputs.outgrid.get_dict(),
                    'outgrid_nest': out_n
                })

    def post_processing(self):
        """post processing"""
        self.report("starting post-processsing")
        builder = FlexpartPostCalculation.get_builder()
        builder.code = self.inputs.post_processing_code
        builder.input_dir = self.ctx.calculations[-1].outputs.remote_folder

        if self.ctx.offline_integration_time > 0:

            builder.input_dir = self.ctx.calculations[-2].outputs.remote_folder
            builder.input_offline_dir = self.ctx.calculations[-1].outputs.remote_folder

        builder.metadata.options = self.inputs.flexpartpost.metadata.options

        running = self.submit(builder)
        self.to_context(calculations=engine.append_(running))

    def run_cosmo_simulation(self):
        """Run calculations for equation of state."""

        self.report(f"starting flexpart cosmo {self.ctx.simulation_date}")

        builder = FlexpartCosmoCalculation.get_builder()
        builder.code = self.inputs.fcosmo_code

        # update command file
        new_dict = self.ctx.command.get_dict()
        new_dict["simulation_date"] = self.ctx.simulation_date
        new_dict["age_class"] = self.inputs.integration_time * 3600
        new_dict.update(self.inputs.meteo_inputs)

        # model settings
        builder.model_settings = {
            "release_settings": self.ctx.release_settings,
            "locations": self.ctx.locations,
            "command": orm.Dict(dict=new_dict),
            "input_phy": self.ctx.input_phy,
        }

        builder.outgrid = orm.Dict(
            list(self.ctx.outgrid.get_dict().values())[0])
        if 'outgrid_nest' in self.inputs:
            builder.outgrid_nest = orm.Dict(
                list(self.inputs.outgrid_nest.get_dict().values())[0])
        builder.species = self.ctx.species
        builder.land_use = self.ctx.land_use
        builder.meteo_path = self.inputs.meteo_path

        # Walltime, memory, and resources.
        builder.metadata.description = "Test workflow to submit a flexpart calculation"
        builder.metadata.options = self.inputs.flexpartcosmo.metadata.options

        # Ask the workflow to continue when the results are ready and store them in the context
        running = self.submit(builder)
        self.to_context(calculations=engine.append_(running))

    def run_ifs_simulation(self):
        """Run calculations for equation of state."""
        # Set up calculation.
        self.report(f"running flexpart ifs for {self.ctx.simulation_date}")
        builder = FlexpartIfsCalculation.get_builder()
        builder.code = self.inputs.fifs_code

        # changes in the command file
        new_dict = self.ctx.command.get_dict()
        new_dict["simulation_date"] = self.ctx.simulation_date

        if self.ctx.offline_integration_time > 0:
            new_dict["age_class"] = self.ctx.offline_integration_time * 3600
            new_dict["dumped_particle_data"] = True

            self.ctx.parent_calc_folder = self.ctx.calculations[
                -1
            ].outputs.remote_folder
            builder.parent_calc_folder = self.ctx.parent_calc_folder
            self.report(f"starting from: {self.ctx.parent_calc_folder}")

            builder.meteo_path = self.inputs.meteo_path_offline
            new_dict.update(self.inputs.meteo_inputs_offline)

        else:
            new_dict["age_class"] = self.inputs.integration_time * 3600
            builder.meteo_path = self.inputs.meteo_path
            new_dict.update(self.inputs.meteo_inputs)

        # model settings
        builder.model_settings = {
            "release_settings": self.ctx.release_settings,
            "locations": self.ctx.locations,
            "command": orm.Dict(dict=new_dict),
        }

        builder.outgrid = orm.Dict(
            list(self.ctx.outgrid.get_dict().values())[0])
        if 'outgrid_nest' in self.inputs:
            builder.outgrid_nest = orm.Dict(
                list(self.inputs.outgrid_nest.get_dict().values())[0])
        builder.species = self.ctx.species
        builder.land_use = self.inputs.land_use_ifs

        # Walltime, memory, and resources.
        builder.metadata.description = "Test workflow to submit a flexpart calculation"
        builder.metadata.options = self.inputs.flexpartifs.metadata.options

        # Ask the workflow to continue when the results are ready and store them in the context
        running = self.submit(builder)
        self.to_context(calculations=engine.append_(running))

    def results(self):
        """Process results."""
        for indx, calculation in enumerate(self.ctx.calculations):
            self.out(f"calculation_{indx}_output_file", calculation.outputs.output_file)

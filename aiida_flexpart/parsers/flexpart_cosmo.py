# -*- coding: utf-8 -*-
"""
Parsers provided by aiida_flexpart.

Register parsers via the "aiida.parsers" entry point in setup.json.
"""
from aiida.engine import ExitCode
from aiida.parsers.parser import Parser
from aiida.plugins import CalculationFactory
from aiida.common import exceptions
from aiida.orm import SinglefileData

FlexpartCalculation = CalculationFactory('flexpart.cosmo')


class FlexpartCosmoParser(Parser):
    """
    Parser class for parsing output of calculation.
    """
    def __init__(self, node):
        """
        Initialize Parser instance

        Checks that the ProcessNode being passed was produced by a FlexpartCalculation.

        :param node: ProcessNode of calculation
        :param type node: :class:`aiida.orm.ProcessNode`
        """
        super().__init__(node)
        if not issubclass(node.process_class, FlexpartCalculation):
            raise exceptions.ParsingError('Can only parse FlexpartCalculation')

    def parse(self, **kwargs):
        """
        Parse outputs, store results in database.

        :returns: an exit code, if parsing fails (or nothing if parsing succeeds)
        """
        output_filename = self.node.get_option('output_filename')

        # Check that folder content is as expected
        files_retrieved = self.retrieved.list_object_names()
        files_expected = [output_filename]
        # Note: set(A) <= set(B) checks whether A is a subset of B
        if not set(files_expected) <= set(files_retrieved):
            self.logger.error("Found files '{}', expected to find '{}'".format(
                files_retrieved, files_expected))
            return self.exit_codes.ERROR_MISSING_OUTPUT_FILES

        # add output file
        self.logger.info(f"Parsing '{output_filename}'")
        with self.retrieved.open(output_filename, 'r') as handle:
            content = handle.read()
            output_node = SinglefileData(file=handle)
            if 'CONGRATULATIONS' not in content:
                self.out('output_file', output_node)
                return ExitCode(1)

        self.out('output_file', output_node)
        return ExitCode(0)

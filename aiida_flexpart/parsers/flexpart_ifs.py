# -*- coding: utf-8 -*-
"""
Parsers provided by aiida_flexpart.

Register parsers via the "aiida.parsers" entry point in setup.json.
"""
from aiida import parsers, plugins, common, orm, engine

FlexpartCalculation = plugins.CalculationFactory('flexpart.ifs')


class FlexpartIfsParser(parsers.Parser):
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
            raise common.ParsingError('Can only parse FlexpartCalculation')

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
            self.logger.error(
                f"Found files '{files_retrieved}', expected to find '{files_expected}'"
            )
            return self.exit_codes.ERROR_MISSING_OUTPUT_FILES

        # check aiida.out content
        self.logger.info(f"Parsing '{output_filename}'")
        with self.retrieved.open(output_filename, 'r') as handle:
            content = handle.read()
            output_node = orm.SinglefileData(file=handle)
            if 'CONGRATULATIONS' not in content:
                self.out('output_file', output_node)
                return engine.ExitCode(1)

        self.out('output_file', output_node)
        return engine.ExitCode(0)

"""
ArcGIS Toolbox for integrating the CEA with ArcGIS.

ArcGIS starts by creating an instance of Toolbox, which in turn names the tools to include in the interface.

These tools shell out to ``cli.py`` because the ArcGIS python version is old and can't be updated. Therefore
we would decouple the python version used by CEA from the ArcGIS version.

See the script ``install_toolbox.py`` for the mechanics of installing the toolbox into the ArcGIS system.
"""
import os
import subprocess
import tempfile

__author__ = "Daren Thomas"
__copyright__ = "Copyright 2016, Architecture and Building Systems - ETH Zurich"
__credits__ = ["Daren Thomas"]
__license__ = "MIT"
__version__ = "0.1"
__maintainer__ = "Daren Thomas"
__email__ = "cea@arch.ethz.ch"
__status__ = "Production"


# DataHelperTool = cea.GUI.data_helper_tool.DataHelperTool
# EmissionsTool = cea.GUI.emissions_tool.EmissionsTool
# EmbodiedEnergyTool = cea.GUI.embodied_energy_tool.EmbodiedEnergyTool
# HeatmapsTool = cea.GUI.heatmaps_tool.HeatmapsTool
# DemandGraphsTool = cea.GUI.demand_graphs_tool.DemandGraphsTool
# RadiationTool = cea.GUI.radiation_tool.RadiationTool
# ScenarioPlotsTool = cea.GUI.scenario_plots_tool.ScenarioPlotsTool
# BenchmarkGraphsTool = cea.GUI.benchmark_graphs_tool.BenchmarkGraphsTool
# MobilityTool = cea.GUI.mobility_tool.MobilityTool

class Toolbox(object):
    def __init__(self):
        self.label = 'City Energy Analyst'
        self.alias = 'cea'
        # self.tools = [DataHelperTool, DemandTool, EmissionsTool, EmbodiedEnergyTool, HeatmapsTool, DemandGraphsTool,
        #               RadiationTool, ScenarioPlotsTool, BenchmarkGraphsTool, MobilityTool]
        self.tools = [DemandTool]


class DemandTool(object):
    """integrate the demand script with ArcGIS"""

    def __init__(self):
        self.label = 'Demand'
        self.description = 'Calculate the Demand'
        self.canRunInBackground = False

    def getParameterInfo(self):
        import arcpy
        scenario_path = arcpy.Parameter(
            displayName="Path to the scenario",
            name="scenario_path",
            datatype="DEFolder",
            parameterType="Required",
            direction="Input")
        weather_name = arcpy.Parameter(
            displayName="Weather file (choose from list or enter full path to .epw file)",
            name="weather_name",
            datatype="String",
            parameterType="Required",
            direction="Input")
        weather_name.filter.list = get_weather_names()

        return [scenario_path, weather_name]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        scenario_path = parameters[0].valueAsText
        if scenario_path is None:
            return
        if not os.path.exists(scenario_path):
            parameters[0].setErrorMessage('Scenario folder not found: %s' % scenario_path)
            return
        if not os.path.exists(get_radiation(scenario_path)):
            parameters[0].setErrorMessage("No radiation data found for scenario. Run radiation script first.")
        if not os.path.exists(get_surface_properties(scenario_path)):
            parameters[0].setErrorMessage("No radiation data found for scenario. Run radiation script first.")
        return

    def execute(self, parameters, _):
        scenario_path = parameters[0].valueAsText
        weather_name = parameters[1].valueAsText
        if weather_name in get_weather_names():
            weather_path = get_weather(weather_name)
        elif os.path.exists(weather_name) and weather_name.endswith('.epw'):
            weather_path = weather_name
        else:
            weather_path = get_weather()

        run_cli(scenario_path, 'demand', '--weather', weather_path)


def add_message(msg, **kwargs):
    import arcpy
    """Log to arcpy.AddMessage() instead of print to STDOUT"""
    if len(kwargs):
        msg %= kwargs
    arcpy.AddMessage(msg)
    log_file = os.path.join(tempfile.gettempdir(), 'cea.log')
    with open(log_file, 'a') as log:
        log.write(msg)


def get_weather_names():
    """Shell out to cli.py and collect the list of weather files registered with the CEA"""
    def get_weather_names_inner():
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        command = [get_python_exe(), '-u', '-m', 'cea.cli', 'weather-files']
        p = subprocess.Popen(command, stdout=subprocess.PIPE, startupinfo=startupinfo)
        while True:
            line = p.stdout.readline()
            if line == '':
                # end of input
                break
            yield line.rstrip()
    return list(get_weather_names_inner())


def get_weather(weather_name='default'):
    """Shell out to cli.py and find the path to the weather file"""
    return _cli_output('', 'weather-path', weather_name)


def get_radiation(scenario_path):
    """Shell out to cli.py and find the path to the ``radiation.csv`` file for the scenario."""
    return _cli_output(scenario_path, 'locate', 'get_radiation')


def get_surface_properties(scenario_path):
    """Shell out to cli.py and find the path to the ``surface_properties.csv`` file for the scenario."""
    return _cli_output(scenario_path, 'locate', 'get_surface_properties')


def get_python_exe():
    """Return the path to the python interpreter that was used to install CEA"""
    try:
        with open(os.path.expanduser('~/cea_python.pth'), 'r') as f:
            python_exe = f.read().strip()
            return python_exe
    except:
        raise AssertionError("Could not find 'cea_python.pth' in home directory.")


def _cli_output(scenario_path, *args):
    """Run the CLI in a subprocess without showing windows and return the output as a string, whitespace
    is stripped from the output"""
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    result = subprocess.check_output(
        [get_python_exe(), '-m', 'cea.cli', '--scenario', scenario_path] + list(args),
        startupinfo=startupinfo)
    return result.strip()


def run_cli(scenario_path, *args):
    """Run the CLI in a subprocess without showing windows"""
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    process = subprocess.Popen(
        [get_python_exe(), '-u', '-m', 'cea.cli', '--scenario', scenario_path] + list(args),
        startupinfo=startupinfo,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE)
    while True:
        next_line = process.stdout.readline()
        if next_line == '' and process.poll() is not None:
            break
        add_message(next_line.rstrip())
    stdout, stderr = process.communicate()
    add_message(stdout)
    add_message(stderr)
"""This file contains functions for getting configuration parameters from
    a config file, or if not defined a default value"""

import os

import yaml


def get_ca_file():
    return _get_parameter_with_default(
        "ca_file", "/etc/irods/localhost_and_chain.crt")


def get_default_yoda_version():
    return str(_get_parameter_with_default("default_yoda_version", "1.8"))


def _get_parameter_with_default(parameter, default_value):
    config_value = _get_parameter_from_config(parameter)
    return config_value if config_value is not None else default_value


def _get_parameter_from_config(parameter):
    config_filename = os.path.expanduser("~/.yodaclienttools.yml")
    if not os.path.exists(config_filename):
        return None
    with open(config_filename, "r") as configfile:
        try:
            data = yaml.safe_load(configfile)
            return data.get(parameter, None)
        except yaml.YAMLError as e:
            print("Error occurred when opening configuration file.")
            print(e)

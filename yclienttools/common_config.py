"""This file contains functions for getting configuration parameters from
    a config file, or if not defined a default value"""

import os
import sys
from typing import Optional

from cryptography import x509
from cryptography.hazmat.backends import default_backend
import yaml


def get_ca_file() -> str:
    configured_ca_file = _get_parameter_from_config("ca_file")
    if configured_ca_file is None:
        for standard_location in ["/etc/irods/localhost_and_chain.crt",
                                  "/etc/ssl/certs/ca-certificates.crt",
                                  "/etc/pki/tls/certs/ca-bundle.crt"]:
            if os.path.isfile(standard_location):
                if is_irods_certificate(standard_location) and not is_self_signed(standard_location):
                    # If the certificate is not self-signed we should
                    # use the default CA location instead
                    continue

                return standard_location

        print("Error: could not find CA bundle in a standard location. You will need to configure it (see the README file for details)")
        sys.exit(1)

    else:
        return configured_ca_file


def is_irods_certificate(path: str) -> bool:
    return path == "/etc/irods/localhost_and_chain.crt"


def is_self_signed(path: str) -> bool:
    with open(path, "rb") as f:
        cert_data = f.read()
    cert = x509.load_pem_x509_certificate(cert_data, default_backend())
    return cert.subject == cert.issuer


def get_default_yoda_version() -> str:
    return str(_get_parameter_with_default("default_yoda_version", "2.0"))


def _get_parameter_with_default(parameter: str, default_value: str) -> str:
    config_value = _get_parameter_from_config(parameter)
    return config_value if config_value is not None else default_value


def _get_parameter_from_config(parameter: str) -> Optional[str]:
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
            sys.exit(1)

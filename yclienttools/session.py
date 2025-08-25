import json
import os
import ssl
import sys

from getpass import getpass

from irods import password_obfuscation
from irods.session import iRODSSession

from yclienttools import common_config


def setup_session(yoda_version_override, session_timeout=120):
    """Use irods environment files to configure a iRODSSession"""

    ca_file = common_config.get_ca_file()

    env_json = os.path.expanduser("~/.irods/irods_environment.json")
    try:
        with open(env_json, 'r') as f:
            irods_env = json.load(f)
    except OSError:
        sys.exit("Can not find or access {}. Please use iinit".format(env_json))

    irodsA = os.path.expanduser("~/.irods/.irodsA")
    try:
        with open(irodsA, "r") as r:
            scrambled_password = r.read()
            password = password_obfuscation.decode(scrambled_password)
    except OSError:
        print(
            "Could not open {} .".format(irodsA),
            file=sys.stderr
        )
        password = getpass(prompt="Please provide your irods password:")

    ssl_context = ssl.create_default_context(purpose=ssl.Purpose.SERVER_AUTH, cafile=ca_file, capath=None, cadata=None)
    ssl_settings = {'client_server_negotiation': 'request_server_negotiation',
                    'client_server_policy': 'CS_NEG_REQUIRE',
                    'encryption_algorithm': 'AES-256-CBC',
                    'encryption_key_size': 32,
                    'encryption_num_hash_rounds': 16,
                    'encryption_salt_size': 8,
                    'ssl_context': ssl_context}
    session = iRODSSession(
        host=irods_env["irods_host"],
        port=irods_env["irods_port"],
        user=irods_env["irods_user_name"],
        password=password,
        zone=irods_env["irods_zone_name"],
        **ssl_settings
    )

    session.connection_timeout = session_timeout
    return session

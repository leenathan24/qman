#! /usr/bin/python3

"""
Usage:
    qman --help
    qman --test-connection
    qman [options] (info|status|enable|disable) -u <id>...
    qman [options] (info|status|enable|disable) -f <path>

Options:
    -h, --help                     Display this help message
    -u <id>, --user=<id>           Qualtrics UserID
    -f <path>, --file=<path>       Input file
    -c <path>, --config=<path>     Path to Qualtrics API configuration file
    --raw                          Disable output formatting
    --test-connection              Test API connection to Qualtrics
"""

import os
import sys
import requests
import json
import yaml
from pprint import pprint
from pathlib import Path
from docopt import docopt

CONFIG_PATH = Path('./config.yaml')
CONFIG = None


def get_config(config_path):
    """Retrieve configuration data.

    Args:
        config_path (pathlib.Path): Path to configuration file

    Returns:
        dict: Configuration data
    """

    with config_path.open() as config_file:
        config = yaml.load(config_file, Loader=yaml.FullLoader)
    return config


def get_user(userid):
    """Retrieve information about a Qualtrics user.

    The --raw flag can be passed from command line to show all user data (this will be a lot).

    Args:
        userid (str): Qualtrics user ID

    Returns:
        dict: User information
    """

    response = requests.get(
        url=f"{CONFIG['baseurl']}/users/{userid}",
        headers={'X-API-TOKEN': f"{CONFIG['token']}"}
    )
    response.raise_for_status()
    return json.loads(response.text)['result']


def enable_user(userid):
    """Enable a Qualtrics user.

    Args:
        userid (str): Qualtrics user ID
    """

    response = requests.put(
        url=f"{CONFIG['baseurl']}/users/{userid}",
        headers={
            'X-API-TOKEN': f"{CONFIG['token']}", 
            'Content-Type': 'application/json'
        },
        data="{\"status\": \"active\"}"
    )
    response.raise_for_status()


def disable_user(userid):
    """Disable a Qualtrics user.

    Args:
        userid (str): Qualtrics user ID
    """

    response = requests.put(
        url=f"{CONFIG['baseurl']}/users/{userid}",
        headers={
            'X-API-TOKEN': f"{CONFIG['token']}", 
            'Content-Type': 'application/json'
        },
        data="{\"status\": \"disabled\"}"
    )
    response.raise_for_status()


def is_enabled(userid):
    """Check if given user ID is active.

    Args:
        userid (str): Qualtrics user ID

    Returns:
        bool: True if enabled, False otherwise
    """

    response = get_user(userid)
    return True if response['accountStatus'] == 'active' else False


def get_all_users():
    """Retrieve all users regardless of status.

    Returns:
        list: User information
    """

    users = []
    request_url = CONFIG['baseurl'] + '/users'
    while request_url:
        response = requests.get(
            url=request_url,
            headers={'X-API-TOKEN': f"{CONFIG['token']}"}
        )
        response.raise_for_status()
        request_url = response.json()['result']['nextPage']
        users += response.json()['result']['elements']
    return users        


def test_connection():
    """Test connection to Qualtrics via API.
    """

    response = requests.get(
        url=f"{CONFIG['baseurl']}/whoami",
        headers={'X-API-TOKEN': f"{CONFIG['token']}"}
    )
    pprint(json.loads(response.text))


if __name__ == '__main__':
    args = docopt(doc=__doc__, argv=sys.argv[1:])

    if args['--config']:
        CONFIG_PATH = Path(args['--config'])
    CONFIG = get_config(CONFIG_PATH)

    if args['--test-connection']:
        test_connection()
        sys.exit(0)

    if args['--user']:
        users = args['--user']
    elif args['--file']:
        infile = Path(args['--file'])
        assert infile.exists()
        users = [u.strip() for u in infile.open().readlines()]
    else:
        raise Exception(
            'User(s) must be provided using either --user or --file parameter.')

    result = {}

    if args['info']:
        try:
            for user in users:
                response = get_user(user)
                if args['--raw']:
                    result[user] = response
                else:
                    result[user] = {x: response[x] for x in CONFIG['attributes']}
        except requests.HTTPError as err:
            result[user] = str(err)
        pprint(result)
    elif args['status']:
        try:
            for user in users:
                response = get_user(user)
                result[user] = response['accountStatus']
        except requests.HTTPError as err:
            result[user] = str(err)
        pprint(result)
    elif args['enable']:
        try:
            for user in users:
                enable_user(user)
        except requests.HTTPError as err:
            result[user] = str(err)
        if result:
            pprint(result)
    elif args['disable']:
        try:
            for user in users:
                disable_user(user)
        except requests.HTTPError as err:
            result[user] = str(err)
        if result:
            pprint(result)

    sys.exit(0)

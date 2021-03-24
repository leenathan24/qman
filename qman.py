#! /usr/bin/python3

"""
Usage:
    qman setup
    qman whoami
    qman [options] (info|status|enable|disable|delete) -u <id>...
    qman [options] (info|status|enable|disable|delete) -f <path>

Options:
    -h, --help                     Display this help message
    -u <id>, --user=<id>           Qualtrics UserID
    -f <path>, --file=<path>       Input file
    --no-filter                    Disable attribute filtering
"""

import os
import sys
import requests
import json
import yaml
from getpass import getpass
from time import sleep
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
        config = yaml.safe_load(config_file)
    return config


def setup():
    baseurl = input("Base URL: ")
    token = getpass("API Token (input will not be shown): ")
    attr_filter = ['username', 'email', 'firstName', 'lastName', 'accountStatus']
    with CONFIG_PATH.open('w') as f:
        yaml_config = yaml.dump({'baseurl': baseurl, 'token': token, 'filter': attr_filter}, f)
    print(f"Setup completed. Default attribute filter set to {attr_filter}. Configurations can be modified as needed by editing the {CONFIG_PATH.name} file.")

class QualtricsManager:

    def __init__(self, baseurl, token):
        """QualtricsManager class init method.

        Args:
            baseurl (str): https://[DATACENTER].qualtrics.com/API/v3
            token (str): Qualtrics API token
        """

        self.baseurl = baseurl
        self.session = requests.Session()
        self.session.headers.update({'X-API-TOKEN': token})

    def whoami(self):
        """Send request to whoami endpoint and return result.

        Returns:
            Python object decoded from JSON response, typically a dict.
        """

        response = self.session.get(f"{self.baseurl}/whoami")
        return json.loads(response.text)

    def users(self, userid=None):
        """Retrieve a particular user, or all users.

        Args:
            userid (str, optional): Qualtrics user ID. Defaults to None.

        Returns: dict for single user, list for all users
        """

        if userid:
            response = self.session.get(f"{self.baseurl}/users/{userid}")
            response.raise_for_status()
            return json.loads(response.text)['result']
        else:
            users = []
            request_url = f"{self.baseurl}/users"
            while request_url:
                response = self.session.get(request_url)
                response.raise_for_status()
                request_url = response.json()['result']['nextPage']
                users += response.json()['result']['elements']
            return users

    # TODO
    def create_user(self, username, passwd, fname, lname, email, usertype, lang):
        pass

    def delete_user(self, userid):
        """Delete a Qualtrics user.

        Args:
            userid (str): Qualtrics user ID
        """
        
        response = self.session.delete(f"{self.baseurl}/users/{userid}")
        response.raise_for_status()

    def enable_user(self, userid):
        """Enable a Qualtrics user.

        Args:
            userid (str): Qualtrics user ID
        """

        response = self.session.put(f"{self.baseurl}/users/{userid}",
                                    headers={'Content-Type': 'application/json'},
                                    data="{\"status\": \"active\"}"
                                    )
        response.raise_for_status()

    def disable_user(self, userid):
        """Disable a Qualtrics user.

        Args:
            userid (str): Qualtrics user ID
        """

        response = self.session.put(f"{self.baseurl}/users/{userid}",
                                    headers={
                                        'Content-Type': 'application/json'},
                                    data="{\"status\": \"disabled\"}"
                                    )
        response.raise_for_status()

    def user_enabled(userid):
        """Check if given user ID is active.

        Args:
            userid (str): Qualtrics user ID

        Returns:
            bool: True if enabled, False otherwise
        """

        response = get_user(userid)
        return True if response['accountStatus'] == 'active' else False


if __name__ == '__main__':

    args = docopt(doc=__doc__, argv=sys.argv[1:])

    # Get/create config
    if not CONFIG_PATH.exists() or args['setup']:
        print("Performing initial setup...")
        sleep(1)
        print('\n')
        setup()
        if args['setup']:
            sys.exit(0)
    CONFIG = get_config(CONFIG_PATH)

    mgr = QualtricsManager(CONFIG['baseurl'], CONFIG['token'])

    if args['whoami']:
        pprint(mgr.whoami())
        sys.exit(0)

    if args['--user']:
        users = args['--user']
    elif args['--file']:
        infile = Path(args['--file'])
        assert infile.exists()
        users = [u.strip() for u in infile.open().readlines()]
    else:
        raise Exception("User(s) must be provided using either --user or --file parameter.")

    result = {}

    try:
        if args['info']:
            for user in users:
                response = mgr.users(user)
                if args['--no-filter']:
                    result[user] = response
                else:
                    result[user] = {x: response[x] for x in CONFIG['filter']}
        elif args['status']:
            for user in users:
                response = mgr.users(user)
                result[user] = response['accountStatus']
        elif args['enable']:
            for user in users:
                mgr.enable_user(user)
        elif args['disable']:
            for user in users:
                mgr.disable_user(user)
        elif args['delete']:
            answer = input("You are about to DELETE one or more users. Are you sure you want to do this? [y/n]: ").lower()
            while answer not in ['y', 'yes', 'n', 'no']:
                answer = input("Please answer with 'y', 'yes', 'n', or 'no': ")
            if answer in ['y', 'yes']:
                for user in users:
                    mgr.delete_user(user)
            else:
                print('No actions taken.')
    except requests.HTTPError as err:
        pprint(err)
        result[user] = str(err)
    if result:
        pprint(result)

    sys.exit(0)

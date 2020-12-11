import json
import os
import sys
import time
import stat
from datetime import datetime

from helpers.singleton import Singleton
from helpers.cli import CLI

class Config(metaclass=Singleton):

    CONFIG_FILE = '.run.conf'
    UNIQUE_ID_FILE = '.uniqid'
    # UPSERT_DB_USERS_TRIGGER_FILE = '.upsert_db_users'
    # LETSENCRYPT_DOCKER_DIR = 'nginx-certbot'
    ENV_FILES_DIR = 'support-api-env'
    # DEFAULT_PROXY_PORT = '8080'
    # DEFAULT_NGINX_PORT = '80'
    # DEFAULT_NGINX_HTTPS_PORT = '443'
    # KOBO_DOCKER_BRANCH = '2.020.45-proagenda2030'
    # KOBO_INSTALL_VERSION = '4.2.0'
    # MAXIMUM_AWS_CREDENTIAL_ATTEMPTS = 3

    def __init__(self):
        self.__first_time = None
        self.__dict = self.read_config()

    def get_dict(self):
        return self.__dict

    def read_config(self):
        """
        Reads config from file `Config.CONFIG_FILE` if exists

        Returns:
            dict
        """
        dict_ = {}
        try:
            base_dir = os.path.dirname(
                os.path.dirname(os.path.realpath(__file__)))
            config_file = os.path.join(base_dir, Config.CONFIG_FILE)
            with open(config_file, 'r') as f:
                dict_ = json.loads(f.read())
        except IOError:
            pass

        self.__dict = dict_
        unique_id = self.read_unique_id()
        
        if not unique_id:
            self.__dict['unique_id'] = int(time.time())

        return dict_
    
    def read_unique_id(self):
        """
        Reads unique id from file `Config.UNIQUE_ID_FILE`

        Returns:
            str
        """
        unique_id = None

        try:
            unique_id_file = os.path.join(self.__dict['support_api_path'],
                                          Config.UNIQUE_ID_FILE)
        except KeyError:
            if self.first_time:
                return None
            else:
                CLI.framed_print('Bad configuration! The path of support_api '
                                 'path is missing. Please delete `.run.conf` '
                                 'and start from scratch',
                                 color=CLI.COLOR_ERROR)
                sys.exit(1)

        try:
            with open(unique_id_file, 'r') as f:
                unique_id = f.read().strip()
        except FileNotFoundError:
            pass

        return unique_id

    def build(self):
        """
        Build configuration based on user's answers

        Returns:
            dict: all values from user's responses needed to create
            configuration files
        """
        self.__welcome()
        self.__dict = self.get_upgraded_dict()

        self.__create_directory()
        
        self.__questions_api_port()
        
        self.write_config()

        return self.__dict

    def get_upgraded_dict(self):
        """
        Sometimes during upgrades, some keys are changed/deleted/added.
        This method helps to get a compliant dict to expected config

        Returns:
            dict
        """
        upgraded_dict = self.get_template()
        upgraded_dict.update(self.__dict)

        # # Upgrade to use two databases
        # upgraded_dict = Upgrading.two_databases(upgraded_dict, self.__dict)

        # # Upgrade to use new terminology primary/secondary
        # upgraded_dict = Upgrading.new_terminology(upgraded_dict)

        # Upgrade to use booleans in `self.__dict`
        # upgraded_dict = Upgrading.use_booleans(upgraded_dict)

        return upgraded_dict

    def get_env_files_path(self):
        current_path = os.path.realpath(os.path.normpath(os.path.join(
            self.__dict['support_api_path'],
            '..',
            Config.ENV_FILES_DIR
        )))

        old_path = os.path.realpath(os.path.normpath(os.path.join(
            self.__dict['support_api_path'],
            '..',
            'kobo-deployments'
        )))

        # if old location is detected, move it to new path.
        if os.path.exists(old_path):
            shutil.move(old_path, current_path)

        return current_path

    def get_prefix(self, role):
        roles = {
            'frontend': 'supportfe',
            'backend': 'supportbe'
        }

        try:
            prefix_ = roles[role]
        except KeyError:
            CLI.colored_print('Invalid composer file', CLI.COLOR_ERROR)
            sys.exit(1)

        if not self.__dict['docker_prefix']:
            return prefix_

        return '{}-{}'.format(self.__dict['docker_prefix'], prefix_)

    def __questions_api_port(self):
        """
        Customize API port
        """
        self.__dict['support_api_port'] = CLI.colored_input('Support API Port?',
                                            CLI.COLOR_QUESTION,
                                            self.__dict['support_api_port'])

    def write_config(self):
        """
        Writes config to file `Config.CONFIG_FILE`.
        """
        # Adds `date_created`. This field will be use to determine
        # first usage of the setup option.
        if self.__dict.get('date_created') is None:
            self.__dict['date_created'] = int(time.time())
        self.__dict['date_modified'] = int(time.time())

        try:
            base_dir = os.path.dirname(
                os.path.dirname(os.path.realpath(__file__)))
            config_file = os.path.join(base_dir, Config.CONFIG_FILE)
            with open(config_file, 'w') as f:
                f.write(json.dumps(self.__dict, indent=2, sort_keys=True))

            os.chmod(config_file, stat.S_IWRITE | stat.S_IREAD)

        except IOError:
            CLI.colored_print('Could not write configuration file',
                              CLI.COLOR_ERROR)
            sys.exit(1)

    def write_unique_id(self):
        try:
            unique_id_file = os.path.join(self.__dict['support_api_path'],
                                          Config.UNIQUE_ID_FILE)
            with open(unique_id_file, 'w') as f:
                f.write(str(self.__dict['unique_id']))

            os.chmod(unique_id_file, stat.S_IWRITE | stat.S_IREAD)
        except (IOError, OSError):
            CLI.colored_print('Could not write unique_id file', CLI.COLOR_ERROR)
            return False

        return True

    def __create_directory(self):
        """
        Create repository directory if it doesn't exist.
        """
        CLI.colored_print('Where do you want to install?', CLI.COLOR_QUESTION)
        while True:
            support_api_path = CLI.colored_input(
                '',
                CLI.COLOR_QUESTION,
                self.__dict['support_api_path']
            )

            if support_api_path.startswith('.'):
                base_dir = os.path.dirname(
                    os.path.dirname(os.path.realpath(__file__)))
                support_api_path = os.path.normpath(
                    os.path.join(base_dir, support_api_path))

            question = 'Please confirm path [{}]'.format(support_api_path)
            response = CLI.yes_no_question(question)
            if response is True:
                if os.path.isdir(support_api_path):
                    break
                else:
                    try:
                        os.makedirs(support_api_path)
                        break
                    except OSError:
                        CLI.colored_print(
                            'Could not create directory {}!'.format(
                                support_api_path), CLI.COLOR_ERROR)
                        CLI.colored_print(
                            'Please make sure you have permissions '
                            'and path is correct',
                            CLI.COLOR_ERROR)

        self.__dict['support_api_path'] = support_api_path
        self.write_unique_id()
        self.__validate_installation()

    @classmethod
    def get_template(cls):

        return {
            'customized_ports': False,
            'support_api_port': 8500,
            'docker_prefix': '',
            'server_role': 'frontend',

            'support_api_path': os.path.realpath(os.path.normpath(os.path.join(
                os.path.dirname(os.path.realpath(__file__)),
                '..',
                '..',
                'support-api-env'))
            ),

            # 'support_api_path': os.path.realpath(os.path.normpath(os.path.join(
            #     os.path.dirname(os.path.realpath(__file__)),
            #     '..',
            #     '..',
            #     'kobo-docker'))
            # ),
        }
        # Keep properties sorted alphabetically

    @property
    def first_time(self):
        """
        Checks whether setup is running for the first time

        Returns:
            bool
        """
        if self.__first_time is None:
            self.__first_time = self.__dict.get('date_created') is None
        return self.__first_time

    @property
    def frontend(self):
        """
        Checks whether setup is running on a frontend server

        Returns:
            dict: all values from user's responses needed to create
            configuration files
        """
        return self.__dict['server_role'] == 'frontend'
    
    def __validate_installation(self):
        """
        Validates if installation is not run over existing data.
        The check is made only the first time the setup is run.
        :return: bool
        """
        if self.first_time:
            postgres_dir_path = os.path.join(self.__dict['support_api_path'],
                                             '.vols', 'db')
            postgres_data_exists = os.path.exists(
                postgres_dir_path) and os.path.isdir(postgres_dir_path)

            if postgres_data_exists:
                # Not a reliable way to detect whether folder contains
                # kobo-install files. We assume that if
                # `docker-compose.backend.template.yml` is there, Docker
                # images are the good ones.
                # TODO Find a better way
                docker_composer_file_path = os.path.join(
                    self.__dict['support_api_path'],
                    'docker-compose.backend.template.yml')
                if not os.path.exists(docker_composer_file_path):
                    message = (
                        'WARNING!\n\n'
                        'You are installing over existing data.\n'
                        '\n'
                        'It is recommended to backup your data and import it '
                        'to a fresh installed (by Support API install) database.\n'
                        '\n'
                        'support-api-install uses these images:\n'
                        '    - PostgreSQL: mdillon/postgis:9.5\n'
                        '\n'
                        'Be sure to upgrade to these versions before going '
                        'further!'
                    )
                    CLI.framed_print(message)
                    response = CLI.yes_no_question(
                        'Are you sure you want to continue?',
                        default=False
                    )
                    if response is False:
                        sys.exit(0)
                    else:
                        CLI.colored_print(
                            'Privileges escalation is needed to prepare DB',
                            CLI.COLOR_WARNING)
                        # Write `kobo_first_run` file to run postgres
                        # container's entrypoint flawlessly.
                        os.system(
                            'echo $(date) | sudo tee -a {} > /dev/null'.format(
                                os.path.join(self.__dict['support_api_path'],
                                             '.vols', 'db', 'kobo_first_run')
                            ))

    @staticmethod
    def __welcome():
        message = (
            'Welcome to SUPPORT API for KoBoToolbox.\n'
            '\n'
            'You are going to be asked some questions that will determine how '
            'to build the configuration of `Support API`.\n'
            '\n'
            'Some questions already have default values (within brackets).\n'
            'Just press `enter` to accept the default value or enter `-` to '
            'remove previously entered value.\n'
            'Otherwise choose between choices or type your answer. '
        )
        CLI.framed_print(message, color=CLI.COLOR_INFO)

    
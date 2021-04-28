import json
import os
import stat
import string
import sys
import time
from datetime import datetime
from random import choice

from helpers.singleton import Singleton
from helpers.cli import CLI
from helpers.aws_validation import AWSValidation

class Config(metaclass=Singleton):

    CONFIG_FILE = '.run.conf'
    UNIQUE_ID_FILE = '.uniqid'
    ENV_FILES_DIR = 'support-api-env'
    MAXIMUM_AWS_CREDENTIAL_ATTEMPTS = 3

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

        self.__questions_postgres()

        self.__questions_kobo_postgres()

        self.__questions_aws()

        self.__questions_postgres_backups()
        
        self.__questions_kobo_api()

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
            'frontend': 'support',
            'backend': 'support',
            'dashboards': 'support'
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

    def __questions_postgres(self):
        """
        PostgreSQL credentials to be confirmed
        """
        #support_db_user = self.__dict['support_db_user']
        #'support_db_server'
                
        CLI.colored_print('Support PostgreSQL database name?',
                          CLI.COLOR_QUESTION)
        support_db_name = CLI.get_response(
            r'~^\w+$',
            self.__dict['support_db_name'],
            to_lower=False
        )

        CLI.colored_print("PostgreSQL user's password?", CLI.COLOR_QUESTION)
        self.__dict['support_db_password'] = CLI.get_response(
            r'~^.{8,}$',
            self.__dict['support_db_password'],
            to_lower=False,
            error_msg='Too short. 8 characters minimum.')


        self.__dict['support_db_port'] = CLI.colored_input('Support PostgreSQL db Port?',
                                            CLI.COLOR_QUESTION,
                                            self.__dict['support_db_port'])

    def __questions_kobo_postgres(self):
        """
        KoBoToolbox's credentials
        """
        # kobo_db_server
        self.__dict['kobo_db_server'] = CLI.colored_input('KoBoToolbox PostgreSQL server?',
                                            CLI.COLOR_QUESTION,
                                            self.__dict['kobo_db_server'])
        
        # kobo_db_name - Kobo Form
        CLI.colored_print('KoBoToolbox\'s KoboFORM PostgreSQL database name?',
                          CLI.COLOR_QUESTION)
        self.__dict['kobo_db_name'] = CLI.get_response(
            r'~^\w+$',
            self.__dict['kobo_db_name'],
            to_lower=False
        )

        # kobo_cat_db_name - Kobo Form
        CLI.colored_print('KoBoToolbox\'s KoboCAT PostgreSQL database name?',
                          CLI.COLOR_QUESTION)
        self.__dict['kobo_cat_db_name'] = CLI.get_response(
            r'~^\w+$',
            self.__dict['kobo_cat_db_name'],
            to_lower=False
        )
        
        # kobo_db_port
        self.__dict['kobo_db_port'] = CLI.colored_input('KoBoToolbox PostgreSQL Port?',
                                            CLI.COLOR_QUESTION,
                                            self.__dict['kobo_db_port'])
        # kobo_db_user
        self.__dict['kobo_db_user'] = CLI.colored_input('KoBoToolbox PostgreSQL User?',
                                            CLI.COLOR_QUESTION,
                                            self.__dict['kobo_db_user'])

        # kobo_db_password
        self.__dict['kobo_db_password'] = CLI.colored_input('KoBoToolbox PostgreSQL Password?',
                                            CLI.COLOR_QUESTION,
                                            self.__dict['kobo_db_password'])


    # TODO: Se debe usar toggle-backup-activation.sh de kobo-docker
        # TODO: El template de postgresql debe tener su propio entrypoint. Hacer lo mismo que se hizo en dashboards
    # TODO: En toggle-backup-activation.sh registrar el cron para sacar backup de postgresql
    # TODO: Se debe hacer el valor para S3 y/o path local
    def __questions_postgres_backups(self):
        """
        Asks all questions about backups.
        """
        if self.backend_questions or (self.frontend_questions and not self.aws):

            self.__dict['use_backup'] = CLI.yes_no_question(
                'Do you want to activate backups?',
                default=self.__dict['use_backup']
            )
            if self.__dict['use_backup']:
                if self.advanced_options:
                    if self.backend_questions and not self.frontend_questions:
                        self.__questions_aws()
                    
                    self.__dict['use_wal_e'] = False

                    schedule_regex_pattern = (
                        r'^((((\d+(,\d+)*)|(\d+-\d+)|(\*(\/\d+)?)))'
                        r'(\s+(((\d+(,\d+)*)|(\d+\-\d+)|(\*(\/\d+)?)))){4})$')
                    message = (
                        'Schedules use linux cron syntax with UTC datetimes.\n'
                        'For example, schedule at 12:00 AM E.S.T every Sunday '
                        'would be:\n'
                        '0 5 * * 0\n'
                        '\n'
                        'Please visit https://crontab.guru/ to generate a '
                        'cron schedule.'
                    )
                    CLI.colored_print('PostgreSQL backup schedule?',
                                        CLI.COLOR_QUESTION)
                    self.__dict[
                        'postgres_backup_schedule'] = CLI.get_response(
                        '~{}'.format(schedule_regex_pattern),
                        self.__dict['postgres_backup_schedule'])

                    if self.aws:
                        self.__questions_aws_backup_settings()
                    
    def __questions_kobo_api(self):
        """
        KoBoToolbox's API
        """
        # kobo_api_uri
        self.__dict['kobo_api_uri'] = CLI.colored_input('KoBoToolbox KPI Uri?',
                                            CLI.COLOR_QUESTION,
                                            self.__dict['kobo_api_uri'])
            
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

    def __questions_aws(self):
        """
        Asks if user wants to see AWS option
        and asks for credentials if needed.
        """
        self.__dict['use_aws'] = CLI.yes_no_question(
            'Do you want to use AWS S3 storage?',
            default=self.__dict['use_aws']
        )
        self.__questions_aws_configuration()
        self.__questions_aws_validate_credentials()

    def __questions_aws_configuration(self):

        if self.__dict['use_aws']:
            self.__dict['aws_access_key'] = CLI.colored_input(
                'AWS Access Key', CLI.COLOR_QUESTION,
                self.__dict['aws_access_key'])
            self.__dict['aws_secret_key'] = CLI.colored_input(
                'AWS Secret Key', CLI.COLOR_QUESTION,
                self.__dict['aws_secret_key'])
            self.__dict['aws_bucket_name'] = CLI.colored_input(
                'AWS Bucket name', CLI.COLOR_QUESTION,
                self.__dict['aws_bucket_name'])
        else:
            self.__dict['aws_access_key'] = ''
            self.__dict['aws_secret_key'] = ''
            self.__dict['aws_bucket_name'] = ''

    def __questions_aws_validate_credentials(self):
        """
        Prompting user whether they would like to validate their entered AWS
        credentials or continue without validation.
        """
        # Resetting validation when setup is rerun
        self.__dict['aws_credentials_valid'] = False
        aws_credential_attempts = 0

        if self.__dict['use_aws']:
            self.__dict['aws_validate_credentials'] = CLI.yes_no_question(
                'Would you like to validate your AWS credentials?',
                default=self.__dict['aws_validate_credentials'],
            )

        if self.__dict['use_aws'] and self.__dict['aws_validate_credentials']:
            while (
                not self.__dict['aws_credentials_valid']
                and aws_credential_attempts
                <= self.MAXIMUM_AWS_CREDENTIAL_ATTEMPTS
            ):
                aws_credential_attempts += 1
                self.validate_aws_credentials()
                attempts_remaining = (
                    self.MAXIMUM_AWS_CREDENTIAL_ATTEMPTS
                    - aws_credential_attempts
                )
                if (
                    not self.__dict['aws_credentials_valid']
                    and attempts_remaining > 0
                ):
                    CLI.colored_print(
                        'Invalid credentials, please try again.',
                        CLI.COLOR_WARNING,
                    )
                    CLI.colored_print(
                        'Attempts remaining for AWS validation: {}'.format(
                            attempts_remaining
                        ),
                        CLI.COLOR_INFO,
                    )
                    self.__questions_aws_configuration()
            else:
                if not self.__dict['aws_credentials_valid']:
                    CLI.colored_print(
                        'Please restart configuration', CLI.COLOR_ERROR
                    )
                    sys.exit(1)
                else:
                    CLI.colored_print(
                        'AWS credentials successfully validated',
                        CLI.COLOR_SUCCESS
                    )

    def __questions_aws_backup_settings(self):

        self.__dict['aws_backup_bucket_name'] = CLI.colored_input(
            'AWS Backups bucket name', CLI.COLOR_QUESTION,
            self.__dict['aws_backup_bucket_name'])

        if self.__dict['aws_backup_bucket_name'] != '':

            backup_from_primary = self.__dict['backup_from_primary']

            CLI.colored_print('How many yearly backups to keep?',
                              CLI.COLOR_QUESTION)
            self.__dict['aws_backup_yearly_retention'] = CLI.get_response(
                r'~^\d+$', self.__dict['aws_backup_yearly_retention'])

            CLI.colored_print('How many monthly backups to keep?',
                              CLI.COLOR_QUESTION)
            self.__dict['aws_backup_monthly_retention'] = CLI.get_response(
                r'~^\d+$', self.__dict['aws_backup_monthly_retention'])

            CLI.colored_print('How many weekly backups to keep?',
                              CLI.COLOR_QUESTION)
            self.__dict['aws_backup_weekly_retention'] = CLI.get_response(
                r'~^\d+$', self.__dict['aws_backup_weekly_retention'])

            CLI.colored_print('How many daily backups to keep?',
                              CLI.COLOR_QUESTION)
            self.__dict['aws_backup_daily_retention'] = CLI.get_response(
                r'~^\d+$', self.__dict['aws_backup_daily_retention'])

            # if (not self.multi_servers or
            #         (self.primary_backend and backup_from_primary) or
            #         (self.secondary_backend and not backup_from_primary)):
            #     CLI.colored_print('PostgresSQL backup minimum size (in MB)?',
                                #   CLI.COLOR_QUESTION)
            CLI.colored_print(
                'Files below this size will be ignored when '
                'rotating backups.',
                CLI.COLOR_INFO)
            self.__dict[
                'aws_postgres_backup_minimum_size'] = CLI.get_response(
                r'~^\d+$',
                self.__dict['aws_postgres_backup_minimum_size'])
            
            CLI.colored_print('Chunk size of multipart uploads (in MB)?',
                              CLI.COLOR_QUESTION)
            self.__dict['aws_backup_upload_chunk_size'] = CLI.get_response(
                r'~^\d+$', self.__dict['aws_backup_upload_chunk_size'])

            response = CLI.yes_no_question(
                'Use AWS LifeCycle deletion rule?',
                default=self.__dict['aws_backup_bucket_deletion_rule_enabled']
            )
            self.__dict['aws_backup_bucket_deletion_rule_enabled'] = response

    @classmethod
    def get_template(cls):

        return {
            'advanced': False,
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
            'support_db_name': 'support',
            'support_db_user': 'user',
            'support_db_password': Config.generate_password(),
            'support_db_port': 5440,
            'support_db_internal_port': 5432,
            'support_db_server': 'support-postgres',
            'support_db_internal_server': 'support-postgres',
            'kobo_db_server': '127.0.0.1',
            'kobo_db_port': '5432',
            'kobo_db_name': 'koboform',
            'kobo_cat_db_name': 'kobocat',
            'kobo_db_user': 'kobo',
            'kobo_db_password': '',
            'kobo_api_uri': '',
            'use_backup': False,
            'use_aws': False,
            'aws_credentials_valid': False,
            'aws_validate_credentials': True,
            'aws_access_key': '',
            'aws_secret_key': '',
            'aws_bucket_name': '',
            'multi': False,
            'backup_from_primary': True,
            'postgres_backup_schedule': '0 2 * * 0',
            'aws_backup_bucket_name': '',
            'aws_backup_yearly_retention': '2',
            'aws_backup_monthly_retention': '12',
            'aws_backup_weekly_retention': '4',
            'aws_backup_daily_retention': '30',
            'aws_postgres_backup_minimum_size': '50',
            'aws_backup_upload_chunk_size': '15',
            'aws_backup_bucket_deletion_rule_enabled': False,
        }

    @classmethod
    def generate_password(cls):
        """
        Generate 12 characters long random password

        Returns:
            str
        """
        characters = string.ascii_letters \
                     + '!$%+-_^~@#{}[]()/\'\'`~,;:.<>' \
                     + string.digits
        required_chars_count = 12

        return ''.join(choice(characters)
                       for _ in range(required_chars_count))

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
    
    @property
    def aws(self):
        """
        Checks whether questions are backend only

        Returns:
            bool
        """
        return self.__dict['use_aws']

    @property
    def multi_servers(self):
        """
        Checks whether installation is for separate frontend and backend servers

        Returns:
            bool
        """
        return self.__dict['multi']

    @property
    def backend_questions(self):
        """
        Checks whether questions are backend only

        Returns:
            bool
        """
        return not self.multi_servers or not self.frontend

    @property
    def advanced_options(self):
        """
        Checks whether advanced options should be displayed

        Returns:
            bool
        """
        return self.__dict['advanced']

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

    def validate_aws_credentials(self):
        validation = AWSValidation(
            aws_access_key_id=self.__dict['aws_access_key'],
            aws_secret_access_key=self.__dict['aws_secret_key'],
        )
        self.__dict['aws_credentials_valid'] = validation.validate_credentials()

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

    
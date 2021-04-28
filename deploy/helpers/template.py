# -*- coding: utf-8 -*-
import fnmatch
import json
import os
import re
import stat
import sys
from string import Template as PyTemplate
from urllib.parse import quote_plus

from helpers.cli import CLI
from helpers.config import Config


class Template:
    UNIQUE_ID_FILE = '.uniqid'

    @classmethod
    def render(cls, config, force=False):
        """
        Write configuration files based on `config`

        Args:
            config (helpers.config.Config)
            force (bool)
        """

        dict_ = config.get_dict()
        template_variables = cls.__get_template_variables(config)

        environment_directory = config.get_env_files_path()
        unique_id = cls.__read_unique_id(environment_directory)
        if (
            not force and unique_id
            and str(dict_.get('unique_id', '')) != str(unique_id)
        ):
            message = (
                'WARNING!\n\n'
                'Existing environment files are detected. Files will be '
                'overwritten.'
            )
            CLI.framed_print(message)
            response = CLI.yes_no_question(
                'Do you want to continue?',
                default=False
            )
            if not response:
                sys.exit(0)

        cls.__write_unique_id(environment_directory, dict_['unique_id'])

        base_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
        templates_path_parent = os.path.join(base_dir, 'templates')

        # Environment
        templates_path = os.path.join(templates_path_parent,
                                      Config.ENV_FILES_DIR,
                                      '')
        for root, dirnames, filenames in os.walk(templates_path):
            destination_directory = cls.__create_directory(
                environment_directory,
                root,
                templates_path)

            cls.__write_templates(template_variables,
                                  root,
                                  destination_directory,
                                  filenames)

    @classmethod
    def render_maintenance(cls, config):

        dict_ = config.get_dict()
        template_variables = cls.__get_template_variables(config)

        base_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
        templates_path_parent = os.path.join(base_dir, 'templates')

        # kobo-docker
        templates_path = os.path.join(templates_path_parent, 'kobo-docker')
        for root, dirnames, filenames in os.walk(templates_path):
            filenames = [filename
                         for filename in filenames if 'maintenance' in filename]
            destination_directory = dict_['kobodocker_path']
            cls.__write_templates(template_variables,
                                  root,
                                  destination_directory,
                                  filenames)

    @classmethod
    def __create_directory(cls, template_root_directory, path='', base_dir=''):

        # Handle case when path is root and equals ''.
        path = os.path.join(path, '')

        destination_directory = os.path.realpath(os.path.join(
            template_root_directory,
            path.replace(base_dir, '')
        ))

        if not os.path.isdir(destination_directory):
            try:
                os.makedirs(destination_directory)
            except OSError:
                CLI.colored_print(
                    'Can not create {}. '
                    'Please verify permissions!'.format(destination_directory),
                    CLI.COLOR_ERROR)
                sys.exit(1)

        return destination_directory

    @staticmethod
    def __get_template_variables(config):
        """
        Write configuration files based on `config`

        Args:
            config (helpers.config.Config)
        """
        dict_ = config.get_dict()

        def _get_value(property_, true_value='', false_value='#',
                       comparison_value=True):
            return true_value \
                if dict_[property_] == comparison_value \
                else false_value

        return {
            'SUPPORT_API_PORT': dict_['support_api_port'],
            'SUPPORT_DB_NAME': dict_['support_db_name'],
            'SUPPORT_DB_USER': dict_['support_db_user'],
            'SUPPORT_DB_PASSWORD': dict_['support_db_password'],
            'POSTGRES_PASSWORD_URL_ENCODED': quote_plus(dict_['support_db_password']),
            'SUPPORT_DB_PORT': dict_['support_db_port'],
            'SUPPORT_DB_INTERNAL_PORT': dict_['support_db_internal_port'],
            'SUPPORT_DB_SERVER': dict_['support_db_server'],
            'SUPPORT_DB_INTERNAL_SERVER': dict_['support_db_internal_server'],
            'KOBO_DB_SERVER': dict_['kobo_db_server'],
            'KOBO_DB_PORT': dict_['kobo_db_port'],
            'KOBO_DB_NAME': dict_['kobo_db_name'],
            'KOBO_CAT_DB_NAME': dict_['kobo_cat_db_name'],
            'KOBO_DB_USER': dict_['kobo_db_user'],
            'KOBO_DB_PASSWORD': dict_['kobo_db_password'],
            'KOBO_API_URI': dict_['kobo_api_uri'],
            'POSTGRES_BACKUP_SCHEDULE': dict_['postgres_backup_schedule'],
            'AWS_POSTGRES_BACKUP_MINIMUM_SIZE': dict_['aws_postgres_backup_minimum_size'],
            'AWS_BACKUP_YEARLY_RETENTION': dict_['aws_backup_yearly_retention'],
            'AWS_BACKUP_MONTHLY_RETENTION': dict_['aws_backup_monthly_retention'],
            'AWS_BACKUP_WEEKLY_RETENTION': dict_['aws_backup_weekly_retention'],
            'AWS_BACKUP_DAILY_RETENTION': dict_['aws_backup_daily_retention'],
            'AWS_ACCESS_KEY_ID': dict_['aws_access_key'],
            'AWS_SECRET_ACCESS_KEY': dict_['aws_secret_key'],
            'USE_AWS': _get_value('use_aws'),
            'AWS_BACKUP_BUCKET_DELETION_RULE_ENABLED': _get_value(
                'aws_backup_bucket_deletion_rule_enabled', 'True', 'False'),
            'USE_BACKUP': '' if dict_['use_backup'] else '#',
            'USE_AWS_BACKUP': '' if (config.aws and
                                     dict_['aws_backup_bucket_name'] != '' and
                                     dict_['use_backup']) else '#',
            'AWS_BACKUP_BUCKET_NAME': dict_['aws_backup_bucket_name'],
            'AWS_BACKUP_UPLOAD_CHUNK_SIZE': dict_['aws_backup_upload_chunk_size'],
            
        }

    @staticmethod
    def __read_unique_id(destination_directory):
        """
        Reads unique id from file `Template.UNIQUE_ID_FILE`
        :return: str
        """
        unique_id = ''

        if os.path.isdir(destination_directory):
            try:
                unique_id_file = os.path.join(destination_directory,
                                              Template.UNIQUE_ID_FILE)
                with open(unique_id_file, 'r') as f:
                    unique_id = f.read().strip()
            except IOError:
                pass
        else:
            unique_id = None

        return unique_id

    @staticmethod
    def __write_templates(template_variables_, root_, destination_directory_,
                          filenames_):
        for filename in fnmatch.filter(filenames_, '*.tpl'):
            with open(os.path.join(root_, filename), 'r') as template:
                t = ExtendedPyTemplate(template.read(), template_variables_)
                with open(os.path.join(destination_directory_, filename[:-4]),
                          'w') as f:
                    f.write(t.substitute(template_variables_))

    @classmethod
    def __write_unique_id(cls, destination_directory, unique_id):
        try:
            unique_id_file = os.path.join(destination_directory,
                                          Template.UNIQUE_ID_FILE)
            # Ensure kobo-deployment is created.
            cls.__create_directory(destination_directory)

            with open(unique_id_file, 'w') as f:
                f.write(str(unique_id))

            os.chmod(unique_id_file, stat.S_IWRITE | stat.S_IREAD)

        except (IOError, OSError):
            CLI.colored_print('Could not write unique_id file', CLI.COLOR_ERROR)
            return False

        return True


class ExtendedPyTemplate(PyTemplate):
    """
    Basic class to add conditional substitution to `string.Template`

    Usage example:
    ```
    {
        'host': 'redis-cache.kobo.local',
        'port': '6379'{% if REDIS_PASSWORD %},{% endif REDIS_PASSWORD %}
        {% if REDIS_PASSWORD %}
        'password': ${REDIS_PASSWORD}
        {% endif REDIS_PASSWORD %}
    }
    ```

    If `REDIS_PASSWORD` equals '123456', output would be:
    ```
    {
        'host': 'redis-cache.kobo.local',
        'port': '6379',
        'password': '123456'
    }
    ```

    If `REDIS_PASSWORD` equals '' (or `False` or `None`), output would be:
    ```
    {
        'host': 'redis-cache.kobo.local',
        'port': '6379'

    }
    ```

    """
    IF_PATTERN = '{{% if {} %}}'
    ENDIF_PATTERN = '{{% endif {} %}}'

    def __init__(self, template, template_variables_):
        for key, value in template_variables_.items():
            if self.IF_PATTERN.format(key) in template:
                if value:
                    if_pattern = r'{}\s*'.format(self.IF_PATTERN.format(key))
                    endif_pattern = r'\s*{}'.format(
                        self.ENDIF_PATTERN.format(key))
                    template = re.sub(if_pattern, '', template)
                    template = re.sub(endif_pattern, '', template)
                else:
                    pattern = r'{}(.|\s)*?{}'.format(
                        self.IF_PATTERN.format(key),
                        self.ENDIF_PATTERN.format(key))
                    template = re.sub(pattern, '', template)
        super(ExtendedPyTemplate, self).__init__(template)

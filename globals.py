#!/usr/bin/env python3


import argparse
import configparser
import logging
import os
import shutil
import subprocess
import sys

# Set up logging configuration
logging.basicConfig(
    format="%(asctime)s | %(levelname)s - %(message)s", datefmt="%Y%m%d%H%M%S"
)
LOGGER = logging.getLogger()
LOGGER.setLevel(logging.INFO)  # Set the default log level to INFO

CONFIG_PATH = os.path.expanduser("~/.config/getmein.conf")
# Copy template config file to the ~/.config if the file doesn't exist
if not os.path.exists(CONFIG_PATH):
    shutil.copy("assets/getmein.conf", CONFIG_PATH)

IMAGE_MAPPING = {
    "centos7": {"project": "centos-cloud", "image_family": "centos-7"},
    "alma8": {"project": "almalinux-cloud", "image_family": "almalinux-8"},
    "rocky8": {"project": "rocky-linux-cloud", "image_family": "rocky-linux-8"},
}


def parse_args():
    """
    Parse arguments.
    :return args:
    """
    parser = argparse.ArgumentParser(
        description="Provision a GCP instance from a Marketplace image."
    )
    subparsers = parser.add_subparsers(dest="action")
    init = subparsers.add_parser("init", help="Initialize the gcloud CLI.")
    init.add_argument("-y", help="Answers yes to all.", action="store_true")
    start = subparsers.add_parser("start", help="Requests a new GCP instance.")
    start.add_argument("instance_name", help="Name for the new instance.")
    start.add_argument(
        "requested_os",
        choices=IMAGE_MAPPING.keys(),
        help="Specify the OS for the deployment. Choices: '%(choices)s'",
    )
    start.add_argument("--ssh-key-path", help="Path to your SSH private key file.")
    start.add_argument("--startup-script", help="Post-install script as a string.")
    start.add_argument("-ssh", help="Generates gcloud ssh keys and connects to the deployed instance.")
    ssh = subparsers.add_parser("ssh", help="Generates gcloud ssh keys and connects to the deployed instance.")
    ssh.add_argument("instance_name", help="Instance name to ssh into.")
    alias = subparsers.add_parser("alias", help="Set an alias for the utility invocation.")
    alias.add_argument("--custom", help="Set a custom alias. Default: '%(default)s'", default="GetMeIn")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging.")
    parser.add_argument("--zone", help="Specify the region/zone for the deployment.")
    parser.add_argument(
        "--project-id", help="Specify the project ID for the deployment."
    )
    args = parser.parse_args()

    return args


ARGS = parse_args()

if ARGS.debug:
    LOGGER.setLevel(logging.DEBUG)

def get_config(zone=None, project_id=None, service_account=None):
    """
    Parse the configuration file ~/.config/getmein
    :param zone:
    :param project_id:
    :param service_account:
    :return zone, project_id, service_account:
    """
    config = configparser.ConfigParser()
    if ARGS.zone:
        zone = ARGS.zone
    elif ARGS.project_id:
        project_id = ARGS.project_id
    else:
        try:
            config.read(CONFIG_PATH)
            project_id = config.get("gcloud", "PROJECT_ID")
            service_account = config.get("gcloud", "SERVICE_ACCOUNT")
            zone = config.get("gcloud", "ZONE")
        except configparser.NoSectionError as no_config_err:
            LOGGER.critical(
                f"There is something wrong with the config file in the default path {CONFIG_PATH}"
            )
            LOGGER.critical(no_config_err)
            sys.exit(99)
        except configparser.NoOptionError as no_opt_err:
            LOGGER.critical("Config file might be tainted.")
            LOGGER.critical(no_opt_err)
            sys.exit(99)
    return zone, project_id, service_account


def set_alias():
    """
    Sets the alias to GetMeIn or a custom one if specified.
    """
    alias = "GetMeIn"
    if ARGS.custom:
        alias = ARGS.custom
    try:
        current_dir = os.getcwd()
        bashrc_path = os.path.expanduser("~/.bashrc")
        alias_string = f"\nalias {alias}=\"python3 {current_dir}/__main__.py\"\n"
        LOGGER.info(f"> ALIAS: Setting an alias {alias} in {bashrc_path}")
        with open(bashrc_path, "a") as bashrc:
            bashrc.write(alias_string)
    except Exception as e:
        LOGGER.debug(e)
    LOGGER.info(f"> ALIAS: Alias has been set, run `source ~/.bashrc, so you can invoke the utility with {alias} <subcommand> [options].")
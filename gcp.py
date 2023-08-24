#!/usr/bin/env python3

import os.path
import re
import subprocess
import sys
import time

from globals import CONFIG_PATH, IMAGE_MAPPING, LOGGER
from globals import get_config, parse_args

ARGS = parse_args()


def initialize_gcloud():
    """
    Initialize the connection to the GCP, set basic information (project_id, zone)
    from either commandline arguments or config file.
    :return:
    """
    gcloud_repo_path = "/etc/yum.repos.d/google-cloud-sdk.repo"
    # Add the google-cloud-sdk.repo
    gcloud_repo_content = "assets/google-cloud-sdk.repo"
    # Check if google-cloud-sdk.repo exists, create if not
    LOGGER.info("> INIT: Checking if the google-cloud-sdk.repo is present.")
    if not os.path.exists(gcloud_repo_path):
        LOGGER.info("> INIT: Adding google-cloud-sdk repository")
        copy_repo_command = ["cp", gcloud_repo_content, gcloud_repo_path]
        LOGGER.debug(f"Running command: {copy_repo_command}")
        subprocess.run(copy_repo_command, shell=True, check=True)
    LOGGER.info("> INIT: google-cloud-sdk.repo is added.")
    # Install google-cloud-cli
    install_gcloud_pkg = ["sudo", "dnf", "install", "google-cloud-cli"]
    # Check if the package is not already installed first
    try:
        subprocess.run(
            ["rpm", "-q", "google-cloud-cli"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )
    except subprocess.CalledProcessError:
        LOGGER.info("> INIT: Installing google-cloud-cli package")
        LOGGER.debug(f"Running command: {install_gcloud_pkg}")
        if ARGS.y:
            LOGGER.info("> INIT: Proceeding with the installation.")
            install_gcloud_pkg += " -y"
        subprocess.run(install_gcloud_pkg, check=True)
    # Initialize gcloud
    zone, project_id, _ = get_config()
    if not zone or not project_id:
        LOGGER.warning(
            f"No value for project_id and/or zone provided.\nPlease use --zone, --project_id or modify the config file at {CONFIG_PATH}.\nExiting"
        )
        sys.exit(99)
    # Authorize to gcloud
    list_auth = subprocess.run(
        ["gcloud", "auth", "list"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if "No credentialed accounts" in list_auth.stderr:
        subprocess.run(["gcloud", "auth", "login"], check=True)

    # Set project to either config or argument value
    subprocess.run(["gcloud", "config", "set", "project", project_id], check=True)
    # Set zone to either config or argument value
    subprocess.run(["gcloud", "config", "set", "compute/zone", zone], check=True)


def set_config(project_id=None, zone=None):
    """
    Change the configuration file from command line.
    """
    if ARGS.zone:
        zone = ARGS.zone

    elif ARGS.project_id:
        project_id = ARGS.project_id

    elif ARGS.config:
        zone, project_id, _ = get_config()

    subprocess.run(["gcloud", "config," "set", "compute/zone", zone], check=True)
    subprocess.run(["gcloud", "config," "set", "project", project_id], check=True)


def create_instance(instance_name):
    """
    Create instance on GCP
    :param instance_name:
    :return:
    """
    zone, project_id, service_account = get_config()

    startup_script = """sudo sed -i '/^#PermitRootLogin/s/^#//' /etc/ssh/sshd_config\nsudo sed -i '/^PermitRootLogin.*/s/.*/PermitRootLogin yes/' /etc/ssh/sshd_config\nsudo systemctl restart sshd"""
    if ARGS.startup_script:
        startup_script = ARGS.startup_script

    def _get_latest_image(requested_os):
        image_family = IMAGE_MAPPING.get(requested_os)["image_family"]
        image_project = IMAGE_MAPPING.get(requested_os)["project"]
        latest_image_command = [
            "gcloud",
            "compute",
            "images",
            "describe-from-family",
            image_family,
            f"--project={image_project}",
        ]
        LOGGER.info(
            f"> START: Getting the latest image for the requested OS {requested_os}"
        )
        try:
            result = subprocess.run(
                latest_image_command,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            # Extract the value of the 'name' field using regex
            name_field_pattern = r"name: (.+)"
            name_field_match = re.search(name_field_pattern, result.stdout)
            latest_image = name_field_match.group(1)
            LOGGER.info(f"> START: Latest image found to be {latest_image} !")
        except:
            raise

        image_string = f"projects/{image_project}/global/images/{latest_image}"

        return image_string

    def _is_unique():
        """ """
        LOGGER.info(
            f"> START: Verifying that the {instance_name} instance doesn't exist."
        )
        list_instance_command = subprocess.run(
            [
                "gcloud",
                "compute",
                "instances",
                "list",
                "--filter",
                f"name~'^{instance_name}$'",
            ],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        # The command returns "Listed 0 items." on STDERR if the instance name is not matched
        if not list_instance_command.stderr:
            LOGGER.critical(f"The instance of the name {instance_name} already exists.")
            LOGGER.critical(
                "Please provide different name for the deployed instance, or use the existing one."
            )
            LOGGER.critical(
                f"The conflicting instance info:\n{list_instance_command.stdout}"
            )
            LOGGER.critical("The utility will exit now.")
            sys.exit(99)
        return True

    _is_unique()

    # Create an instance with a startup script
    image = _get_latest_image(ARGS.requested_os)

    create_instance_command = [
        "gcloud",
        "compute",
        "instances",
        "create",
        instance_name,
        f"--project={project_id}",
        f"--zone={zone}",
        "--machine-type=e2-medium",
        f"--metadata=startup-script={startup_script}",
        "--maintenance-policy=MIGRATE",
        "--provisioning-model=STANDARD",
        f"--service-account={service_account}",
        "--scopes=https://www.googleapis.com/auth/devstorage.read_only,https://www.googleapis.com/auth/logging.write,https://www.googleapis.com/auth/monitoring.write,https://www.googleapis.com/auth/servicecontrol,https://www.googleapis.com/auth/service.management.readonly,https://www.googleapis.com/auth/trace.append",
        f"--create-disk=auto-delete=yes,boot=yes,device-name={instance_name},image={image},mode=rw,size=20,type=projects/leapp-devel-700/zones/us-central1-a/diskTypes/pd-balanced",
        "--no-shielded-secure-boot",
        "--shielded-vtpm",
        "--shielded-integrity-monitoring",
        "--labels=goog-ec-src=vm_add-gcloud",
        "--reservation-affinity=any",
    ]

    LOGGER.info(f"> START: Creating the instance {instance_name}")

    subprocess.run(create_instance_command, check=True)

    if ARGS.ssh:
        _instance_ssh(ARGS.instance_name)


def _instance_ssh(instance_name):
    #

    wait_time = 60
    gcloud_ssh_command = "gcloud", "compute," "ssh", f"root@{instance_name}"
    gcloud_ssh_key_path = os.path.expanduser("~/.ssh/google_compute_engine")
    LOGGER.info(f"Waiting for {wait_time} seconds for the instance to become alive.")
    while wait_time > 0:
        sys.stdout.write(f"\rWaiting: {wait_time} seconds remaining. ")
        sys.stdout.flush()
        time.sleep(1)  # Sleep for 1 second
        wait_time -= 1
    print("\n")
    LOGGER.info(
        f"> START: The script will now call the '{gcloud_ssh_command}' command."
    )
    LOGGER.info(
        f"> START: This will generate new gcloud ssh keys under {gcloud_ssh_key_path}(.pub)\nand inject to the /root/.ssh/authorized_keys"
    )
    if os.path.exists(gcloud_ssh_key_path) and os.path.exists(
        f"{gcloud_ssh_key_path}.pub"
    ):
        LOGGER.info(
            "> START: The ssh keys found at the default location, they won't be regenerated."
        )
    response = input("Do you want to continue with the automation? (Y/n)")
    while response.lower not in ("y", "n"):
        if response.lower() == "y":
            LOGGER.info("Proceeding with the gcloud ssh command.")
            subprocess.run(gcloud_ssh_command, check=True)
            return
        elif response.lower() == "n":
            LOGGER.info("Exiting.")
            sys.exit(99)
        else:
            response = input("Please provide a valid answer. (Y/n)")

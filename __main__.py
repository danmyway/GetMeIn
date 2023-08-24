#!/usr/bin/env python3

from gcp import initialize_gcloud, set_config, create_instance, _instance_ssh
from globals import ARGS, set_alias

def main():
    if ARGS.action == "init":
        initialize_gcloud()
    elif ARGS.action == "set":
        set_config()
    elif ARGS.action == "start":
        create_instance(ARGS.instance_name)
    elif ARGS.action == "ssh":
        _instance_ssh(ARGS.instance_name)
    elif ARGS.action == "alias":
        set_alias()

if __name__ == "__main__":
    main()

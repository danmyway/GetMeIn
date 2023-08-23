# GetMeIn
A utility to easily deploy Alma Linux 8, Rocky Linux 8 and CentOS 7 on GCP.

## Usage 

#### Available images
Deploys instances of official free images of:
* Rocky Linux 8
* Alma Linux 8
* CentOS 7

The utility checks for the latest version of the image available. \
IIUIC these should be with the latest updates.\
As far as the utility is concerned, it should be able to handle deploying other images with the `IMAGE_MAPPING` updated with valid values.

**Schema example:**
```shell
{
  "os_alias": {
    "project": "rhel-9",
    "image_family": "rhel-cloud"
  }
}
```
See [the official documentation](https://cloud.google.com/sdk/gcloud/reference/compute/images/describe-from-family) for more context.
>**__WARNING!__**  
> This has not been tested!

#### VM Specification
By default, the instance is created with these specifications:
* Machine type: `e2-medium`
  * Mem 4 GB
  * 1-2 vCPU (1 shared core)
* Disk Size
  * 20 GB

Can be modified if deemed unsatisfactory.

### Prerequisites

>**__IMPORTANT:__**  
> Right now the configuration secret values are not very well handled. \
> Please copy the template config file from the assets directory of the repository.\
> Reach out to me or access the team BitWarden collection and look for the getmein.conf note for the configuration values.
```commandline
cp assets/getmein.conf ~/.config/getmein.conf
```

### alias
Set an alias to ease working with the utility.
By default, creates a `GetMeIn` alias in `~/.bashrc`
Can be customized with `--custom`.

>**__NOTE:__**  
> The following documentation considers the alias to be set to `GetMeIn`.

### init
 
With the config file set up, you can initialize and authenticate the script running:
```shell
GetMeIn init
```
This will add the `google-cloud-sdk.repo` file to your system and install the `google-cloud-cli` package from there.\
If you have the repofile and/or the package present on your system already, nothing will happen.\
The script will authenticate to the Google Cloud SDK, browser window will pop up asking you for acknowledgement and permission. \
Again, in case you already have a credentialed account, nothing will happen. \
You can (however do not need to) verify prior by running `gcloud auth list`
Lastly, the project_id and zone will be set from the config file (if set up already).
The zone value has a default value hardcoded in the config template.

### start
```shell
# Get Alma Linux 8 instance
GetMeIn start my-alma-instance alma8

# Get Rocky Linux 8 instance
GetMeIn start my-rocky-instance rocky8

# Get CentOS 7 instance
GetMeIn start my-centos-instance centos7
```

If called with `--ssh` the script should automatically resolve root login via ssh issues by calling `gcloud compute ssh root@<instance_name>`.\
This call generates ssh keys at ~/.ssh/google_compute_engine(.pub), injects the key to the `/root/.ssh/authorized_keys` on the host machine and connects you to the machine, if you have the ssh keys already on your system, the utility will just inject them to the host machine.\

>**__NOTE:__**  
> There is a 60-second sleep time between deploying the instance and trying to ssh into it.\
> In most cases that is enough time for the guest system to be able to accept the ssh connection.\
Rarely the ssh will fail, but can be repeated by running either `gcloud compute ssh root@<instance_name>` or `ssh -i ~/.ssh/google_compute_engine root@<instance_ip_address>`

The usual way of connecting through the ssh works as well.
```shell
ssh -i ~/.ssh/google_compute_engine root@<instance_ip_address>

# Or add the key to the ssh agent
ssh-add ~/.ssh/google_compute_engine
ssh root@<instance_ip_address>
```

You can list deployed instances by running `gcloud compute instances list`.
The utility won't allow you to deploy two instances with the same name. 

### ssh
In case you want to deploy multiple instances, you do not need to resolve the ssh straight away.
Instead, you can just deploy the machines and utilize the `ssh` subcommand when ready.

```shell
GetMeIn ssh <instance_name>
```

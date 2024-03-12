<img src="./banner.png" />

`WorkArena` is a suite of browser-based tasks designed for ServiceNow products, acting as a benchmark for automating commonly conducted activities within the product environment.

## Setup

### ServiceNow Instance

1. Go to https://developer.servicenow.com/ and create an account
2. Request a Utah developer instance (initializing it might take a while)
3. Log into your ServiceNow instance via the browser and change the admin password if instructed to do so. If you're already registered in the instance, you can find the instance information (Username, Password, instance URL) in the `My Instances` section of your developer account.
4. Set the following environment variables:
    * `SNOW_INSTANCE_URL`: URL of your ServiceNow developer instance
    * `SNOW_INSTANCE_UNAME`: username for your instance (usually `admin`)
    * `SNOW_INSTANCE_PWD`: password for your instance (you'll receive this by email and you can get it from your ServiceNow developer account)

To set environment variables in Bash, you can use the `export` command. Here's an example:

```
export SNOW_INSTANCE_URL="https://your-instance-url.service-now.com"
export SNOW_INSTANCE_UNAME="your-username"
export SNOW_INSTANCE_PWD="your-password"
```

Another option is to add the environment variables to your conda environment. To do this, you can execute the following command :

```
conda env config vars set ENV_VAR=VALUE
```

### Install Data

Run the following code to install all the data shipped with the benchmark:

```
from browsergym.workarena.install import setup
setup()
```

### Finally

1. Run `pytest -v .` to make sure that your setup works.

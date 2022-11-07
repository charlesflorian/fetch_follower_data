# Introduction

This python utility will fetch information about a user's followers and output it as a .csv file. Due to
limitations in the twitter api, you can only fetch 15,000 followers at a time, with a 15 minute gap between
runs. If the user in question has more than that, you will need to run the utility several times.

## Dependencies

This is a `python3` script. It needs, not surprisingly, `tweepy`, but also `pyyaml` and `pandas`. These are
installed via
```console
$ pip3 install tweepy pyyaml pandas
```

## Usage

The input file should be a configuration file that looks like the following.
```yaml
---
bearer_token: <your bearer token here>
user_fields:
- name
- location
- url
- username
- description
```
This should be saved as `config.yml`; you can add any fields you would like to include in the output data. The
complete list of user fields can be found here: https://developer.twitter.com/en/docs/twitter-api/data-dictionary/object-model/user

Once you have created a config file, you simply need to run
```console
$ python3 fetch_follower_data.py <username>
```

If the desired user has more than 15000 followers (aren't they popular!), then you should run again with
```console
$ python3 fetch_follower_data.py --continue <username>
```

After the final run, you should see a file `username.csv` that consists of the desired follower data.
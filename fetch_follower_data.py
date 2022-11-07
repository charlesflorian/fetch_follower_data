import argparse
import json
import sys

import pandas as pd
import tweepy
import yaml
from tweepy.errors import TooManyRequests


def get_user_id(client: tweepy.Client, username: str) -> int:
    """Fetch the user ID from a given user name."""
    user = client.get_user(username=username)
    return user.data.id


def read_config_data(config_file: str) -> dict:
    """Read in the configuration data."""
    with open(config_file, "r") as f:
        config_data = yaml.safe_load(f)

    fields = set(["username", "public_metrics"])
    try:
        fields.update(config_data["user_fields"])
    except KeyError:
        pass

    tweet_fields = set(["text"])
    try:
        tweet_fields.update(config_data["tweet_fields"])
    except KeyError:
        pass

    try:
        bearer_token = config_data["bearer_token"]
    except KeyError:
        print(f"Missing bearer token in config file {config_file}", file=sys.stderr)
        sys.exit(-1)

    return fields, tweet_fields, bearer_token


def fetch_follower_data(
    config: str,
    username: str,
    pagination_token: str,
):
    """Fetch the follower data for the given user."""

    user_fields, tweet_fields, bearer_token = read_config_data(config)

    client = tweepy.Client(bearer_token=bearer_token)

    user_id = get_user_id(client, username)

    followers = []
    done = False
    while True:
        try:
            response = client.get_users_followers(
                user_id,
                user_fields=list(user_fields),
                pagination_token=pagination_token,
                tweet_fields=list(tweet_fields),
                max_results=1000,
                expansions="pinned_tweet_id",
            )
        except TooManyRequests:
            break

        pinned_tweets = {tweet.id: tweet for tweet in response.includes["tweets"]}
        for datum in response.data:
            new_follower = {field: datum[field] for field in user_fields}
            new_follower.update(new_follower.pop("public_metrics"))
            if datum["pinned_tweet_id"]:
                try:
                    tweet = pinned_tweets[datum["pinned_tweet_id"]]
                    new_follower.update(
                        {
                            f"pinned_tweet_{field}": tweet[field]
                            for field in tweet_fields
                        }
                    )
                except KeyError:
                    pass

            followers.append(new_follower)

        try:
            pagination_token = response.meta["next_token"]
        except KeyError:
            done = True
            break

    if not done:
        if pagination_token:
            print(f"Too many requests: next token is {pagination_token}")
        else:
            print("Too many requests already! Wait 15 minutes.")

    if followers:
        write_follower_data(f"{username}_{pagination_token}", followers)


def write_follower_data(filename: str, follower_data: list):
    """Write the follower data into a .csv and .json file."""
    with open(f"{filename}.json", "w") as f:
        json.dump(follower_data, f)

    for ix, follower in enumerate(follower_data):
        for k, v in follower.items():
            if type(v) == str:
                # Remove all newlines
                follower_data[ix][k] = v.encode("unicode_escape").decode("utf-8")
    df = pd.DataFrame.from_dict(follower_data)
    with open(f"{filename}.csv", "w") as f:
        df.to_csv(f)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config.yml")
    parser.add_argument("-p", "--pagination-token", default=None)
    parser.add_argument("username")

    args = parser.parse_args()

    fetch_follower_data(**vars(args))


if __name__ == "__main__":
    main()
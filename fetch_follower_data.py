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
    if user and user.data:
        return user.data.id
    print(f"Invalid username: {username}", file=sys.stderr)
    sys.exit(-1)


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
    continue_: bool,
):
    """Fetch the follower data for the given user."""

    user_fields, tweet_fields, bearer_token = read_config_data(config)

    client = tweepy.Client(bearer_token=bearer_token)

    user_id = get_user_id(client, username)

    followers = []
    pagination_token = None
    if continue_:
        followers, pagination_token = read_temporary_data(username)

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

    if followers:
        if done:
            write_follower_data(username, followers)
        else:
            write_temporary_data(username, followers, pagination_token)
            print(
                "Too many requests. Try again in 15 minutes with the --continue parameter."
            )
            sys.exit(-1)


def read_temporary_data(username: str):
    try:
        with open(f"{username}-tmp.json") as f:
            data = json.load(f)
            return data["followers"], data["next_token"]
    except FileNotFoundError:
        return [], None


def write_temporary_data(username: str, follower_data: list, pagination_token: str):
    with open(f"{username}-tmp.json", "w") as f:
        tmp_data = {"followers": follower_data, "next_token": pagination_token}
        json.dump(tmp_data, f)


def write_follower_data(filename: str, follower_data: list):
    """Write the follower data into a .csv file."""

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
    parser.add_argument("--continue", dest="continue_", action="store_true")
    parser.add_argument("username")

    args = parser.parse_args()

    fetch_follower_data(**vars(args))


if __name__ == "__main__":
    main()

import boto3
from botocore.exceptions import ClientError


def list_profiles():
    import configparser
    import os
    profiles: set[str] = set()
    for fpath, strip_prefix in [
        ("~/.aws/credentials", False),
        ("~/.aws/config",      True),
    ]:
        path = os.path.expanduser(fpath)
        if not os.path.isfile(path):
            continue
        cp = configparser.ConfigParser()
        cp.read(path)
        for section in cp.sections():
            name = section[len("profile "):].strip() if strip_prefix and section.startswith("profile ") else section
            if name and name.lower() != "default":
                profiles.add(name)
    return sorted(profiles)


def make_client(profile=None, region="us-east-1",
                access_key_id=None, secret_access_key=None):
    if access_key_id and secret_access_key:
        session = boto3.Session(
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
            region_name=region,
        )
    else:
        session = boto3.Session(profile_name=profile or None, region_name=region)
    return session.client("logs")


def list_log_groups(client, prefix=""):
    groups = []
    kwargs = {"limit": 50}
    if prefix:
        kwargs["logGroupNamePrefix"] = prefix
    try:
        paginator = client.get_paginator("describe_log_groups")
        for page in paginator.paginate(**kwargs):
            groups.extend(g["logGroupName"] for g in page["logGroups"])
    except (ClientError, Exception) as e:
        raise RuntimeError(str(e))
    return sorted(groups)


def list_log_streams(client, log_group, prefix=""):
    streams = []
    kwargs = {
        "logGroupName": log_group,
        "orderBy": "LastEventTime",
        "descending": True,
        "limit": 50,
    }
    if prefix:
        kwargs["logStreamNamePrefix"] = prefix
        del kwargs["orderBy"]
        del kwargs["descending"]
    try:
        paginator = client.get_paginator("describe_log_streams")
        for page in paginator.paginate(**kwargs):
            streams.extend(s["logStreamName"] for s in page["logStreams"])
            if len(streams) >= 200:
                break
    except (ClientError, Exception) as e:
        raise RuntimeError(str(e))
    return streams


def fetch_events(client, log_group, log_stream=None, start_ms=None,
                 filter_pattern="", max_events=500):
    """
    Fetch log events. Returns list of (timestamp_ms, message) tuples.
    If log_stream is None, fetches from all streams in the group.
    max_events=None means unlimited (full initial load).
    """
    events = []
    kwargs = {"logGroupName": log_group}
    if start_ms is not None:
        kwargs["startTime"] = start_ms
    if filter_pattern:
        kwargs["filterPattern"] = filter_pattern
    if log_stream:
        kwargs["logStreamNames"] = [log_stream]

    try:
        paginator = client.get_paginator("filter_log_events")
        for page in paginator.paginate(**kwargs):
            for ev in page.get("events", []):
                events.append((ev["timestamp"], ev["message"].rstrip()))
            if max_events is not None and len(events) >= max_events:
                break
    except (ClientError, Exception) as e:
        raise RuntimeError(str(e))

    return events

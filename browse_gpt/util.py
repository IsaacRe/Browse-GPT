from hashlib import md5


def hash_url(url: str):
    return md5(url.split("//")[1].encode("utf-8")).hexdigest()
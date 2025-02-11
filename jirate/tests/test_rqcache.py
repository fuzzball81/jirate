#!/usr/bin/python3
import copy
import os
import time

import pytest  # NOQA

from jirate.rqcache import RequestCache
import jirate.rqcache

class TestSession(object):
    def request(self, method, url, **kwargs):
        return {'value': os.urandom(16), 'resp': 200}

    def get(self, url, **kwargs):
        return self.request('GET', url, **kwargs)

    def put(self, url, **kwargs):
        return self.request('PUT', url, **kwargs)

    def post(self, url, **kwargs):
        return self.request('POST', url, **kwargs)


# Overwrite ResilientSession import
jirate.rqcache.ResilientSession = TestSession


def test_rqcache_nomatch():
    session = TestSession()
    cache = RequestCache(session, filename=None, expire=10)
    # url1 is not matched by our paths so it should always
    # be a cache miss
    ret1 = session.get('url1')
    ret2 = session.get('url1')

    assert ret1 != ret2


def test_rqcache_match():
    session = TestSession()
    cache = RequestCache(session, filename=None, expire=10)
    # /field is a match, so we should get the cached data on
    # the second pull
    ret1 = session.get('https://whatever/rest/api/2/field')
    ret2 = session.get('https://whatever/rest/api/2/field')

    assert ret1 == ret2


def test_rqcache_match_expire():
    session = TestSession()
    cache = RequestCache(session, filename=None, expire=1)
    # We expire in 1 second, so second pull should have new
    # data
    ret1 = session.get('https://whatever/rest/api/2/field')
    time.sleep(1.1)
    ret2 = session.get('https://whatever/rest/api/2/field')

    assert ret1 != ret2


def test_rqcache_purge_expired():
    session = TestSession()
    cache = RequestCache(session, filename=None, expire=1)
    # Here, our baseline has no requests
    baseline = copy.deepcopy(cache.cached_reqs)
    ret1 = session.get('https://whatever/rest/api/2/field')
    # Now our cache has one request, which expires in 1 second
    # Flushing the cache should not matter
    cache.flush()
    assert cache.cached_reqs != baseline

    # Wait for our req to expire
    time.sleep(1.1)
    cache.flush()
    # Now, we should be back to baseline
    assert cache.cached_reqs == baseline


def test_rqcache_load_none(tmp_path):
    session = TestSession()
    cache = RequestCache(session, filename=None, expire=1)
    assert not cache.load(os.path.join(tmp_path, 'cache_test'))


def test_rqcache_load_bad(tmp_path):
    session = TestSession()
    filename = os.path.join(tmp_path, 'cache_test')
    with open(filename, 'w') as fp:
        fp.write('hello, world!')
    cache = RequestCache(session, filename, expire=1)
    # Tests using our initial filename
    assert not cache.load()

    # We unlink the file if it's bad data
    with pytest.raises(FileNotFoundError):
        os.unlink(filename)


def test_rqcache_persist(tmp_path):
    session = TestSession()
    filename = os.path.join(tmp_path, 'cache_test')
    cache = RequestCache(session, filename=filename, expire=30)
    ret1 = session.get('https://whatever/rest/api/2/field')
    cache.save()

    # Load our cache from disk
    session2 = TestSession()
    cache2 = RequestCache(session, filename=filename, expire=1)
    ret2 = session.get('https://whatever/rest/api/2/field')

    # Request should match
    assert ret1 == ret2


def test_rqcache_persist_expire(tmp_path):
    session = TestSession()
    filename = os.path.join(tmp_path, 'cache_test')
    cache = RequestCache(session, filename=filename, expire=1)
    ret1 = session.get('https://whatever/rest/api/2/field')
    cache.save()
    time.sleep(1.1)

    # Load our cache from disk
    session2 = TestSession()
    cache2 = RequestCache(session, filename=filename, expire=1)
    ret2 = session.get('https://whatever/rest/api/2/field')

    # Request should not match
    assert ret1 != ret2

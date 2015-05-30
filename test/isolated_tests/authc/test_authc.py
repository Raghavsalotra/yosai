import pytest
from unittest import mock

from yosai import (
    AuthenticationException,
    MultiRealmAuthenticationException,
    UnsupportedTokenException,
)

from yosai.authc import (
    DefaultAuthenticator,
    DefaultCompositeAccount,
    UsernamePasswordToken,
)

# UsernamePasswordToken Tests
def test_upt_clear_existing_password(username_password_token):
    """ clear a password equal to 'secret' """
    upt = username_password_token
    upt.clear() 
    assert upt.password == bytearray(b'\x00\x00\x00\x00\x00\x00')  


# -----------------------------------------------------------------------------
# DefaultAuthenticator Tests
# -----------------------------------------------------------------------------
def test_da_auth_sra_unsupported_token(
        default_authenticator, mock_token, default_accountstorerealm):
    """ An AuthenticationToken of a type unsupported by the Realm raises an 
        exception
    """
    da = default_authenticator
    realm = default_accountstorerealm
    token = mock_token
    with pytest.raises(UnsupportedTokenException):
        da.authenticate_single_realm_account(realm, token) 

def test_da_authc_sra_supported_token(
        default_authenticator, first_accountstorerealm_succeeds, 
        username_password_token):
    """ a successful authentication returns an account """
    
    da = default_authenticator
    realm = first_accountstorerealm_succeeds 
    token = username_password_token
    assert da.authenticate_single_realm_account(realm, token)

def test_da_autc_mra_succeeds(
        default_authenticator, two_accountstorerealms_succeeds,
        username_password_token):

    da = default_authenticator
    realms = two_accountstorerealms_succeeds 
    token = username_password_token
    result = da.authenticate_multi_realm_account(realms, token)
    assert (result.__class__.__name__ == 'MockAccount')

def test_da_autc_mra_fails(
        default_authenticator, two_accountstorerealms_fails,
        username_password_token):

    da = default_authenticator
    realms = two_accountstorerealms_fails
    token = username_password_token

    with pytest.raises(MultiRealmAuthenticationException):
        da.authenticate_multi_realm_account(realms, token)

def test_da_authc_acct_authentication_fails(
        default_authenticator, username_password_token, monkeypatch):
    """ when None is returned from do_authenticate_account, it means that
        something other than authentication failed, and so an exception is 
        raised """
    da = default_authenticator
    token = username_password_token
    
    def do_nothing(x, y):
        pass

    monkeypatch.setattr(da, 'do_authenticate_account', do_nothing) 
    monkeypatch.setattr(da, 'notify_failure', do_nothing) 
    monkeypatch.setattr(da, 'notify_success', do_nothing) 

    with pytest.raises(AuthenticationException):
        da.authenticate_account(token)

def test_da_authc_acct_authentication_raises_unknown_exception(
        default_authenticator, username_password_token, monkeypatch):
    """ an unexpected exception will be wrapped by an AuthenticationException 
    """
    da = default_authenticator
    token = username_password_token

    def raise_typeerror():
        raise TypeError
    
    def do_nothing(x, y):
        pass

    monkeypatch.setattr(da, 'do_authenticate_account', raise_typeerror) 
    monkeypatch.setattr(da, 'notify_failure', do_nothing) 
    monkeypatch.setattr(da, 'notify_success', do_nothing) 

    with pytest.raises(AuthenticationException) as exc_info:
        da.authenticate_account(token)

    assert 'unexpected' in str(exc_info.value)


def test_da_authc_acct_authentication_succeeds(
        default_authenticator, username_password_token, monkeypatch,
        full_mock_account):
    """ when an Account is returned from do_authenticate_account, it means that
        authentication succeeded
    """
    da = default_authenticator
    token = username_password_token
    
    def get_mock_account(self, x=None):
        return full_mock_account
    
    def do_nothing(x, y):
        pass

    monkeypatch.setattr(da, 'do_authenticate_account', get_mock_account) 
    monkeypatch.setattr(da, 'notify_failure', do_nothing) 
    monkeypatch.setattr(da, 'notify_success', do_nothing) 

    result = da.authenticate_account(token)

    assert isinstance(result, full_mock_account.__class__)

def test_da_do_authc_acct_with_realm(
        default_authenticator, username_password_token,
        one_accountstorerealm_succeeds, monkeypatch):
    """ when the DefaultAuthenticator is missing a realms attribute, an 
        exception will raise in do_authenticate_account 
    """
    
    da = default_authenticator
    token = username_password_token

    da.realms = one_accountstorerealm_succeeds 

    def say_nothing(x, y):
        return 'nothing'
    
    monkeypatch.setattr(da, 'authenticate_single_realm_account', say_nothing)
    result = da.do_authenticate_account(token)
    assert result == 'nothing'

def test_da_do_authc_acct_with_realms(
        default_authenticator, username_password_token,
        two_accountstorerealms_succeeds, monkeypatch):
    
    da = default_authenticator
    token = username_password_token

    da.realms = two_accountstorerealms_succeeds 

    def say_something(self, x=None, y=None):
        return 'something'

    monkeypatch.setattr(da, 'authenticate_multi_realm_account', say_something)
    result = da.do_authenticate_account(token)
    assert result == 'something'


def test_da_do_authc_acct_without_realm(
        default_authenticator, username_password_token):
    """ when the DefaultAuthenticator is missing a realms attribute, an 
        exception will raise in do_authenticate_account 
    """
    
    da = default_authenticator
    token = username_password_token

    with pytest.raises(AuthenticationException):
        da.do_authenticate_account(token)

def test_da_notify_success_with_eventbus(
        default_authenticator, username_password_token, full_mock_account,
        patched_event_bus, monkeypatch):
    
    da = default_authenticator
    token = username_password_token
    account = full_mock_account

    monkeypatch.setattr(da, '_event_bus', patched_event_bus)

    assert da.notify_success(token, account) is None

def test_da_notify_success_without_eventbus(
        default_authenticator, username_password_token, full_mock_account,
        monkeypatch):
    
    da = default_authenticator
    token = username_password_token
    account = full_mock_account

    monkeypatch.setattr(da, '_event_bus', None)
    
    assert da.notify_success(token, account) is None


def test_da_notify_failure_with_eventbus(
        default_authenticator, username_password_token, full_mock_account,
        patched_event_bus, monkeypatch):
    
    da = default_authenticator
    token = username_password_token
    account = full_mock_account

    monkeypatch.setattr(da, '_event_bus', patched_event_bus)

    assert da.notify_failure(token, account) is None

def test_da_notify_failure_without_eventbus(
        default_authenticator, username_password_token, full_mock_account,
        monkeypatch):
    
    da = default_authenticator
    token = username_password_token
    account = full_mock_account

    monkeypatch.setattr(da, '_event_bus', None)
    
    assert da.notify_failure(token, account) is None
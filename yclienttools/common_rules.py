'''Call an iRODS rule with a specific rulename.
   params should be an OrderedDict with the parameters of the rule
   number_output is the number of output parameters of the rule (usually 1 or 2)
'''
from io import StringIO

from collections import OrderedDict

from irods.rule import Rule

from yclienttools import common_queries
from yclienttools.exceptions import SizeNotSupportedException

def call_rule(session, rulename, params, number_outputs):
    body = 'myRule {{\n {} ('.format(rulename)

    for input_var in params.keys():
        body += "*{},".format(input_var)

    outparams = list(map(lambda n : '*outparam{}'.format(str(n+1)), range(number_outputs)))
    body += '{}); writeLine("stdout","{}")}}'.format(
        ",".join(outparams),
        "\n".join(outparams))

    input_params = { "*{}".format(k) : '"{}"'.format(v) for (k,v) in params.items() }
    output_params = 'ruleExecOut'

    myrule = Rule(
        session,
        rule_file = StringIO(body),
        params=input_params,
        output=output_params)

    outArray = myrule.execute()
    buf = outArray.MsParam_PI[0].inOutStruct.stdoutBuf.buf.decode(
        'utf-8').splitlines()

    return buf[:number_outputs]


def _string_list_to_list(s):
    if s.startswith("[") and s.endswith("]"):
        return s[1:-1].split(",")
    else:
        raise ValueError("Unable to convert string representation of list to list")


def call_uuGroupGetMembers(session, groupname):
    parms = OrderedDict([
        ( 'groupname', groupname)] )
    [out] = call_rule(session, 'uuGroupGetMembers', parms, 1)
    if len(out) >= 1023 and not out.endswith("]"):
        raise SizeNotSupportedException("Group member list exceeds 1023 bytes")
    return _string_list_to_list(out)


def call_uuGroupUserRemove(session, groupname, user):
    parms = OrderedDict([
        ( 'groupname', groupname),
        ( 'user', user) ])
    return call_rule(session, 'uuGroupUserRemove', parms, 2)


def call_uuGroupGetMemberType(session, groupname, user):
    parms = OrderedDict([
        ( 'groupname', groupname),
        ( 'user', user) ])
    return call_rule(session, 'uuGroupGetMemberType', parms, 1)[0]

def call_uuGroupUserAdd(session, groupname, username):
    # returns (status, message)
    # status !=0 is error
    parms = OrderedDict([
        ('groupname', groupname),
        ('username', username)])
    return call_rule(session, 'uuGroupUserAdd', parms, 2)


def call_uuGroupUserChangeRole(session, groupname, username, newrole):
    # role can be "manager", "reader", "normal"
    # returns (status, message)
    # status != 0 is error
    parms = OrderedDict([
        ('groupname', groupname),
        ('username', username),
        ('newrole', newrole)])
    return call_rule(session, 'uuGroupUserChangeRole', parms, 2)


def call_uuGroupExists(session, groupname):
    # returns (exists)
    # exists is false or true
    parms = OrderedDict([('groupname', groupname)])
    [out] = call_rule(session, 'uuGroupExists', parms, 1)
    return out == 'true'


def call_uuUserExists(session, username):
    # returns (exists)
    # exists is false or true
    parms = OrderedDict([('username', username)])
    [out] = call_rule(session, 'uuUserExists', parms, 1)
    return out == 'true'


def call_uuGroupAdd(session, groupname, category,
                    subcategory, description, classification):
    # returns (status, message)
    # status != 0 is error
    # status = -1089000 means groupname already exists
    parms = OrderedDict([
        ('groupname', groupname),
        ('category', category),
        ('subcategory', subcategory),
        ('description', description),
        ('classification', classification)])
    return call_rule(session, 'uuGroupAdd', parms, 2)

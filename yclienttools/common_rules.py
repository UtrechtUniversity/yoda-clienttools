'''This class is used as an interface for calling Yoda rules using python-irodsclient
'''
from io import StringIO

from collections import OrderedDict

from irods.rule import Rule

from yclienttools import common_queries
from yclienttools.exceptions import SizeNotSupportedException

class RuleInterface:

    def __init__(self, session, yoda_version= "1.7"):
        """constructor

           :param session: IrodsSession object to call
           :param yoda_version: which Yoda version to assume (1.7, 1.8, 1.9)

Whether to specify the rule engine on rule calls
                          (enable for Yoda 1.8 and higher, disable for Yoda 1.7)
        """
        self.session = session
        self.set_re = False if yoda_version == "1.7" else True
        self.uuGroupAdd_version = "1.7" if yoda_version in ["1.7", "1.8"] else "1.9"
        self.default_rule_engine = 'irods_rule_engine_plugin-irods_rule_language-instance'


    def call_rule(self, rulename, params, number_outputs,
                  rule_engine = None):
        """Run a rule

           :param rulename: name of the rule
           :param params: dictionary of rule input parameters and their values
           :param number_output: number of output parameters
           :param rule_engine: rule engine to run rule on (defaults to legacy rule engine if none provided)
         """
        body = 'myRule {{\n {} ('.format(rulename)

        for input_var in params.keys():
            body += "*{},".format(input_var)

        outparams = list(map(lambda n : '*outparam{}'.format(str(n+1)), range(number_outputs)))
        body += '{}); writeLine("stdout","{}")}}'.format(
            ",".join(outparams),
            "\n".join(outparams))

        input_params = { "*{}".format(k) : '"{}"'.format(v) for (k,v) in params.items() }
        output_params = 'ruleExecOut'

        if self.set_re:
            re_config = { 'instance_name': self.default_rule_engine if rule_engine is None
                                                               else rule_engine }
        else:
            re_config = {}

        myrule = Rule(
            self.session,
            rule_file = StringIO(body),
            params=input_params,
            output=output_params,
            **re_config)

        outArray = myrule.execute()
        buf = outArray.MsParam_PI[0].inOutStruct.stdoutBuf.buf.decode(
            'utf-8').splitlines()

        return buf[:number_outputs]


    def _string_list_to_list(self, s):
        if s.startswith("[") and s.endswith("]"):
            return s[1:-1].split(",")
        else:
            raise ValueError("Unable to convert string representation of list to list")


    def call_uuGroupGetMembers(self, groupname):
       """Returns list of group members"""
       parms = OrderedDict([
           ( 'groupname', groupname)] )
       [out] = self.call_rule('uuGroupGetMembers', parms, 1)
       if len(out) >= 1023 and not out.endswith("]"):
           raise SizeNotSupportedException("Group member list exceeds 1023 bytes")
       return self._string_list_to_list(out)


    def call_uuGroupUserRemove(self, groupname, user):
       """Removes a user from a group"""
       parms = OrderedDict([
           ( 'groupname', groupname),
           ( 'user', user) ])
       return self.call_rule('uuGroupUserRemove', parms, 2)


    def call_uuGroupGetMemberType(self, groupname, user):
       """:returns: member type of a group member"""
       parms = OrderedDict([
           ( 'groupname', groupname),
           ( 'user', user) ])
       return self.call_rule('uuGroupGetMemberType', parms, 1)[0]

    def call_uuGroupUserAdd(self, groupname, username):
       """Adds user to group.

          :param: groupname
          :param: username
          :returns: (status, message) ; status !=0 is error
       """
       parms = OrderedDict([
           ('groupname', groupname),
           ('username', username)])
       return self.call_rule('uuGroupUserAdd', parms, 2)


    def call_uuGroupUserChangeRole(self, groupname, username, newrole):
       """Change role of user in group

          :param groupname: name of group
          :param username: name of user
          :param newrole: new role (can be "manager", "reader", "normal")
          :returns: (status, message) ; status != 0 is error
       """
       parms = OrderedDict([
           ('groupname', groupname),
           ('username', username),
           ('newrole', newrole)])
       return self.call_rule('uuGroupUserChangeRole', parms, 2)


    def call_uuGroupExists(self, groupname):
       """Check whether group name exists on Yoda

          :param groupname: name of group
          :returns: false/true
       """
       parms = OrderedDict([('groupname', groupname)])
       [out] = self.call_rule('uuGroupExists', parms, 1)
       return out == 'true'


    def call_uuUserExists(self, username):
       """Check whether user name exists on Yoda

          :param username: name of user
          :returns: false/true
       """
       parms = OrderedDict([('username', username)])
       [out] = self.call_rule('uuUserExists', parms, 1)
       return out == 'true'


    def call_uuGroupAdd(self, groupname, category,
                       subcategory, description, classification):
       """Adds a group

          :param groupname: name of group
          :param category: category / community
          :param subcategory: subcategory
          :param description: description
          :param classification: security classification

          :returns: (status, message). Status not 0 means error,
                    -1089000 means group name already exists
       """
       if self.uuGroupAdd_version == "1.7":
           parms = OrderedDict([
               ('groupname', groupname),
               ('category', category),
               ('subcategory', subcategory),
               ('description', description),
               ('classification', classification)])
       elif self.uuGroupAdd_version == "1.9":
           parms = OrderedDict([
               ('groupname', groupname),
               ('category', category),
               ('subcategory', subcategory),
               ('schema_id', 'default-2'),
               ('expirationdate', ''),
               ('description', description),
               ('classification', classification)])

       return self.call_rule('uuGroupAdd', parms, 2)

    def call_uuGroupRemove(self, groupname):
       """Removes an empty group

          :param groupname: name of group

          :returns: (status, message). Status not 0 means error.
       """
       parms = OrderedDict([('groupname', groupname)])
       return self.call_rule('uuGroupRemove', parms, 2)

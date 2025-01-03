'''This class is used as an interface for calling Yoda rules using python-irodsclient
'''
from io import StringIO
from collections import OrderedDict
from typing import List

from irods.rule import Rule

from yclienttools.exceptions import SizeNotSupportedException


class RuleInterface:

    def __init__(self, session, yoda_version):
        """constructor

           :param session: IrodsSession object to call
           :param yoda_version: which Yoda version to assume (e.g. 1.7, 1.8, 1.9)

Whether to specify the rule engine on rule calls
                          (enable for Yoda 1.8 and higher, disable for Yoda 1.7)
        """
        self.session = session
        self.set_re = False if yoda_version == "1.7" else True
        self.uuGroupAdd_version = "1.7" if yoda_version in [
            "1.7", "1.8"] else "1.9"
        self.default_rule_engine = 'irods_rule_engine_plugin-irods_rule_language-instance'

        try:
            self.client_hints_rules = self.session.client_hints.get("rules", {})
        except Exception as e:
            print("Error: {}. Hint: python-irodsclient needs to be version 2.1 or later to support client_hints.".format(e))

    def call_rule(self, rulename, params, number_outputs,
                  rule_engine=None) -> List[str]:
        """Run a rule

           :param rulename: name of the rule
           :param params: dictionary of rule input parameters and their values
           :param number_output: number of output parameters
           :param rule_engine: rule engine to run rule on (defaults to legacy rule engine if none provided)
         """
        body = 'myRule {{\n {} ('.format(rulename)

        for input_var in params.keys():
            body += "*{},".format(input_var)

        outparams = list(
            map(lambda n: '*outparam{}'.format(str(n + 1)), range(number_outputs)))
        body += '{}); writeLine("stdout","{}")}}'.format(
            ",".join(outparams),
            "\n".join(outparams))

        input_params = {"*{}".format(k): '"{}"'.format(v)
                        for (k, v) in params.items()}
        output_params = 'ruleExecOut'

        if self.set_re:
            re_config = {'instance_name': self.default_rule_engine if rule_engine is None
                         else rule_engine}
        else:
            re_config = {}

        myrule = Rule(
            self.session,
            rule_file=StringIO(body),
            params=input_params,
            output=output_params,
            **re_config)

        outArray = myrule.execute()
        buf = outArray.MsParam_PI[0].inOutStruct.stdoutBuf.buf.decode(
            'utf-8').splitlines()

        return buf[:number_outputs]

    def _string_list_to_list(self, s: str) -> List[str]:
        if s.startswith("[") and s.endswith("]"):
            return s[1:-1].split(",")
        else:
            raise ValueError(
                "Unable to convert string representation of list to list")

    def call_uuGroupGetMembers(self, groupname: str) -> List[str]:
        """Returns list of group members"""
        parms = OrderedDict([
            ('groupname', groupname)])
        [out] = self.call_rule('uuGroupGetMembers', parms, 1)
        if len(out) >= 1023 and not out.endswith("]"):
            raise SizeNotSupportedException(
                "Group member list exceeds 1023 bytes")
        return self._string_list_to_list(out)

    def call_uuGroupUserRemove(self, groupname: str, user: str) -> List[str]:
        """Removes a user from a group"""
        parms = OrderedDict([
            ('groupname', groupname),
            ('user', user)])
        return self.call_rule('uuGroupUserRemove', parms, 2)

    def call_uuGroupGetMemberType(self, groupname: str, user: str) -> str:
        """:returns: member type of a group member"""
        parms = OrderedDict([
            ('groupname', groupname),
            ('user', user)])
        return self.call_rule('uuGroupGetMemberType', parms, 1)[0]

    def call_uuGroupUserAddByOtherCreator(
            self, groupname: str, username: str, creator_user: str, creator_zone: str) -> List[str]:
        """Adds user to group on the behalf of a creator user.

           :param: groupname
           :param: username
           :param: creator_user
           :param: creator_zone
           :returns: (status, message) ; status !=0 is error
        """
        parms = OrderedDict([
            ('groupname', groupname),
            ('username', username),
            ('creatorUser', creator_user),
            ('creatorZone', creator_zone)])
        return self.call_rule('uuGroupUserAdd', parms, 2)

    def call_uuGroupUserAdd(self, groupname: str, username: str) -> List[str]:
        """Adds user to group.

           :param: groupname
           :param: username
           :returns: (status, message) ; status !=0 is error
        """
        parms = OrderedDict([
            ('groupname', groupname),
            ('username', username)])
        return self.call_rule('uuGroupUserAdd', parms, 2)

    def call_uuGroupUserChangeRole(self, groupname: str, username: str, newrole: str) -> List[str]:
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

    def call_uuGroupExists(self, groupname: str) -> bool:
        """Check whether group name exists on Yoda

           :param groupname: name of group
           :returns: false/true
        """
        parms = OrderedDict([('groupname', groupname)])
        [out] = self.call_rule('uuGroupExists', parms, 1)
        return out == 'true'

    def call_rule_user_exists(self, username: str) -> bool:
        """Check whether user name exists on Yoda

           :param username: name of user
           :returns: false/true
        """
        # Determine which rule to call
        rule_to_call = 'rule_user_exists' if 'rule_user_exists' in self.client_hints_rules else 'uuUserExists'

        # Prepare rule parameters
        parms = OrderedDict([('username', username)])
        if rule_to_call == 'rule_user_exists':
            parms['outparam1'] = ""

        # Call the rule
        [out] = self.call_rule(rule_to_call, parms, 1)

        return out == 'true'

    def call_uuGroupAdd(self, groupname: str, category: str,
                        subcategory: str, description: str, classification, schema_id: str = 'default-2', expiration_date: str = '') -> List[str]:
        """Adds a group

           :param groupname: name of group
           :param category: category / community
           :param subcategory: subcategory
           :param description: description
           :param classification: security classification
           :param schema_id: schema id
           :param expiration_date: expiration date

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
                ('schema_id', schema_id if schema_id not in ("", ".") else "default-2"),
                ('expiration_date', expiration_date),
                ('description', description),
                ('dataClassification', classification),
                ('co_identifier', '')
            ])

        return self.call_rule('uuGroupAdd', parms, 2)

    def call_uuGroupModify(self, groupname: str, property: str, value: str) -> List[str]:
        """Modifies one property of a group

           :param groupname: name of group
           :param property:  property to change
           :param value:     value to change the property to

           :returns: (status, message). Status not 0 means error.
        """
        parms = OrderedDict([('groupname', groupname),
                             ('property', property),
                             ('value', value)])
        return self.call_rule('uuGroupModify', parms, 2)

    def call_uuGroupRemove(self, groupname: str) -> List[str]:
        """Removes an empty group

           :param groupname: name of group

           :returns: (status, message). Status not 0 means error.
        """
        parms = OrderedDict([('groupname', groupname)])
        return self.call_rule('uuGroupRemove', parms, 2)

#!/usr/bin/python
# -*- coding: utf-8 -*-
# vim: ts=4 sw=4 et
"""
TODO:
* make _info and other methods to be bulk operation methods
"""

import sys
import requests
from xml.etree import ElementTree as ET
import pprint
import re
import json


class Helper:
    @staticmethod
    def convert_json2xml(doc, root):
        children = ET.Element(root)
        if isinstance(doc, dict):
            for key, value, in doc.items():
                if isinstance(value, dict):
                    child = Helper.convert_json2xml(doc=value, root=key)
                    children.append(child)
                elif isinstance(value, list):
                    for item in value:
                        child = Helper.convert_json2xml(doc=item, root=key)
                        children.append(child)
                elif isinstance(value, (str, int, float)):
                    child = ET.Element(key)
                    child.text = str(value)
                    children.append(child)
                elif value is None:
                    continue
                else:
                    raise NotImplementedError('Type of {} is not implemented yet, is it a {}?'.format(key, type(value)))
        return children

    @staticmethod
    def prettify(element):
        """Return a pretty-printed XML string for the Element.
        """
        raw_string = ET.tostring(element, 'utf-8')

        text_re = re.compile('>\n\s+([^<>\s].*?)\n\s+</', re.DOTALL)
        return text_re.sub('>\g<1></', raw_string.decode())

#def convert_json2xml(doc, root):
#    children = Tag(name=root)
#    if isinstance(doc, dict):
#        for key, value, in doc.items():
#            if isinstance(value, dict):
#                child = convert_json2xml(doc=value, root=key)
#                children.append(child)
#            elif isinstance(value, list):
#                raise NotImplementedError('Type of {} is not implemented yet, is it a {}?'.format(key, type(value)))
#            elif isinstance(value, (str, int, float)):
#                child = Tag(name=key)
#                child.string = str(value)
#                children.append(child)
#            else:
#                raise NotImplementedError('Type of {} is not implemented yet, is it a {}?'.format(key, type(value)))
#    return children


class Internetx:
    def __init__(self, url, username, password, context, language='en', owner=None, fun_codes=None):
        self.url = url
        self.username = username
        self.password = password
        self.context = context
        self.language = language
        self.owner = None

        if fun_codes is not None:
            self.fun_codes = fun_codes
        else:
            self.fun_codes = {
                'contact_info': '0304',
                'domain_info': '0105',
                'domain_transfer_in': '0104',
                'domain_transfer_out': '0106002',
                'zone_create': '0201',
                'zone_info': '0205',
            }

    def _parse_api_call_properties(self, api_call_properties):
        defaults = {'offset': 0, 'limit': 30, 'subusers': False, }
        for k, v in defaults.items():
            if k in api_call_properties:
                continue
            api_call_properties[k] = v
        return api_call_properties

    def _call(self, task):
        _request = {'auth': {'user': self.username, 'password': self.password, 'context': self.context, }, 'language': self.language, }

        if self.owner:
            _request['owner'] = self.owner

        request = Helper.convert_json2xml(doc=_request, root='request')
        request.append(task)

        http_data = ET.tostring(request)
        print('==> request', http_data, '\n')

        headers = {'Content-Type': 'application/xml'}

        http_response = requests.post(self.url, data=http_data, headers=headers)

        response_tree = ET.fromstring(http_response.text)
        #response_tree = BeautifulSoup(http_response.text, 'lxml-xml')
        print('==> response', ET.tostring(response_tree), '\n')

        return response_tree

    def __parse_onelvl_children(self, tree):
        fields = {}
        for field in tree:
            fields[field.tag] = field.text
        return fields

    def _contact_parse_response(self, object_xml):
        result = {}
        for field in object_xml:
            if field.tag in ['owner']:
                result[field.tag] = self.__parse_onelvl_children(field)
            elif field.tag in ['nic_ref']:
                if field.tag not in result:
                    result[field.tag] = []
                result[field.tag].append(self.__parse_onelvl_children(field))
            else:
                result[field.tag] = field.text
        return result

    def _domain_parse_response(self, object_xml):
        result = {}
        for field in object_xml:
            if field.tag in ['owner']:
                result[field.tag] = self.__parse_onelvl_children(field)
            elif field.tag in ['nserver']:
                if field.tag not in result:
                    result[field.tag] = []
                result[field.tag].append(self.__parse_onelvl_children(field))
            else:
                result[field.tag] = field.text
        return result

    def _zone_parse_response(self, object_xml):
        result = {}
        for field in object_xml:
            if field.tag in ['owner', 'soa']:
                result[field.tag] = self.__parse_onelvl_children(field)
            elif field.tag in ['nserver', 'rr']:
                if field.tag not in result:
                    result[field.tag] = []
                result[field.tag].append(self.__parse_onelvl_children(field))
            else:
                result[field.tag] = field.text
        return result

    def domain_info(self, name, api_call_properties={}):
        api_call_properties = self._parse_api_call_properties(api_call_properties)
        _task = {'code': self.fun_codes['domain_info'], 'domain': {'name': name, }, }
        task = Helper.convert_json2xml(doc=_task, root='task')
        server_response = self._call(task)
        result = self._domain_parse_response(server_response.find('./result/data/domain'))
        return result

    def domain_list(self, api_call_properties={}):
        api_call_properties = self._parse_api_call_properties(api_call_properties)
        _task = {
            'code': self.fun_codes['domain_info'],
            'view': {
                'offset': api_call_properties['offset'],
                'limit': api_call_properties['limit'],
                'children': int(api_call_properties['subusers']),
            },
            'order': {
                'key': 'created',
                'mode': 'asc',
            },
        }
        task = Helper.convert_json2xml(doc=_task, root='task')
        server_response = self._call(task)

        result = []
        for object_xml in server_response.findall('./result/data/domain'):
            fields = self._domain_parse_response(object_xml)
            result.append(fields)
        return result

    def domain_transfer_in(self, params, api_call_properties={}):
        api_call_properties = self._parse_api_call_properties(api_call_properties)
        if isinstance(params, dict):
            _task = {
                'code': self.fun_codes['domain_transfer_in'],
                'default': {
                    'ownerc': params['ownerc'],
                    'adminc': params['adminc'],
                    'techc': params['techc'],
                    'zonec': params['zonec'],
                    'nserver': params['nserver'],
                    'confirm_order': int(True),
                },
                'domain': {
                    'name': params['name'],
                    'authinfo': params['authinfo'],
                },
            }
        else:
            pass  #TODO

        task = Helper.convert_json2xml(doc=_task, root='task')
        server_response = self._call(task)
        result = self._domain_parse_response(server_response.find('./result'))
        return result

    def zone_info(self, name, api_call_properties={}):
        api_call_properties = self._parse_api_call_properties(api_call_properties)
        _task = {'code': self.fun_codes['zone_info'], 'zone': {'name': name, }, }
        task = Helper.convert_json2xml(doc=_task, root='task')
        server_response = self._call(task)
        result = self._zone_parse_response(server_response.find('./result/data/zone'))
        return result

    def zone_list(self, api_call_properties={}):
        api_call_properties = self._parse_api_call_properties(api_call_properties)
        _task = {
            'code': self.fun_codes['zone_info'],
            'view': {
                'offset': api_call_properties['offset'],
                'limit': api_call_properties['limit'],
                'children': int(api_call_properties['subusers']),
            },
            'order': {
                'key': 'created',
                'mode': 'asc',
            },
        }
        task = Helper.convert_json2xml(doc=_task, root='task')
        server_response = self._call(task)

        result = []
        for object_xml in server_response.findall('./result/data/zone'):
            fields = self._domain_parse_response(object_xml)
            result.append(fields)
        return result

    def zone_create(self, params, api_call_properties={}):
        api_call_properties = self._parse_api_call_properties(api_call_properties)
        if isinstance(params, dict):
            _task = {
                'code': self.fun_codes['zone_create'],
                'zone': {
                    'name': params['name'],
                    'ns_action': 'complete',
                    'nserver': params['nserver'],
                    'soa': params['soa'],
                    'rr': params['rr'],
                    'www_include': int(False),
                },
            }
        else:
            pass  #TODO

        task = Helper.convert_json2xml(doc=_task, root='task')
        server_response = self._call(task)
        result = self._zone_parse_response(server_response.find('./result'))
        return result

    def contact_info(self, name, api_call_properties={}):
        api_call_properties = self._parse_api_call_properties(api_call_properties)
        _task = {'code': self.fun_codes['contact_info'], 'handle': {'id': str(name), }, }
        task = Helper.convert_json2xml(doc=_task, root='task')
        server_response = self._call(task)
        result = self._contact_parse_response(server_response.find('./result/data/handle'))
        return result

    def contact_list(self, api_call_properties={}):
        api_call_properties = self._parse_api_call_properties(api_call_properties)
        _task = {
            'code': self.fun_codes['contact_info'],
            'view': {
                'offset': api_call_properties['offset'],
                'limit': api_call_properties['limit'],
                'children': int(api_call_properties['subusers']),
            },
            'order': {
                'key': 'created',
                'mode': 'asc',
            },
        }
        task = Helper.convert_json2xml(doc=_task, root='task')
        server_response = self._call(task)

        result = []
        for object_xml in server_response.findall('./result/data/handle'):
            fields = self._domain_parse_response(object_xml)
            result.append(fields)
        return result

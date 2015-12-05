#!/usr/bin/python
# -*- coding: utf-8 -*-
# vim: ts=4 sw=4 et

from xml.etree import ElementTree as ET
#import pprint
import re


class Helper:
    """
    Helper class providing useful methods
    """

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

        text_re = re.compile(r'>\n\s+([^<>\s].*?)\n\s+</', re.DOTALL)
        return text_re.sub(r'>\g<1></', raw_string.decode())

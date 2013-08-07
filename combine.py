#import xml.etree.ElementTree as et
from lxml import etree as et
import os
import pdb


class CoberturaCombiner(object):
    """
    This class is created so that we can combine 
    multiple Cobertura XML Coverage reports, and 
    generate one report showing coverage for all
    tests against a codebase.
    """
    def __init__(self, filenames):
        assert len(filenames) > 0, 'No files'
        self.roots = [et.parse(f).getroot() for f in filenames]

    def combine(self):
        root_xml = self.roots[0]

        for r in self.roots[1:]:
            # Combine each element with the first one, and update that
            self.combine_element(root_xml, r)

        (n_lines, n_hits) = self.calculate_coverage(root_xml, n_lines=0, n_hits=0)
        ratio = round(n_hits/float(n_lines) if n_lines > 0 else 0, 4)
        root_xml.set('line-rate', str(ratio))
        #self.calculate_coverage(root_xml)
        # Return the string representation
        return et.tostring(root_xml)

    def _create_mapping_key(self, element):
        return '{0}:{1}'.format(element.tag,
                                str([item for item in element.items()
                                    if 'line-rate' not in item 
                                    and 'hits' not in item]))

    def combine_element(self, one, other):
        """
        This function recursively updates either the text or the children
        of an element if another element is found in `one`, or adds it from
        `other` if not found.

        Going to need a bit of work to just turn 0's to 1's on conflict.
        """
        # Create a mapping from tag name to element
        mapping = { self._create_mapping_key(el): el for el in one }

        for el in other:
            key = self._create_mapping_key(el)
            try:
                if len(el) == 0:
                    if mapping[key] is not None and el.tag == 'line':
                        hit = max(mapping[key].get('hits'), el.get('hits'))
                        # set the new value
                        mapping[key].set('hits', str(hit))

                    # Update the text
                    mapping[key].text = el.text
                else:
                    # Recusively process the element, and update it in the same way
                    self.combine_element(mapping[key], el)
            except KeyError:
                # An element with this name is not in the maping
                mapping[key] = el
                # Add it
                one.append(el)

    def calculate_coverage(self, root, n_lines=0, n_hits=0):
        """
        This function goes through the document and updates the 
        coverage numbers for each module in the document

        Need to pass in the coverage list too
        """
        # Grab only the elements which have something valuable to contribute
        gen_root = (e for e in root if len(e.getchildren()) > 0 or len(e.items()) > 0)
        for el in gen_root:
            # Check for line-rate
            if el.get('line-rate', False):
                # count the line coverage, here we need to "start over" counting
                before_lines = n_lines
                before_hits = n_hits

                (n_lines, n_hits) = self.calculate_coverage(el, n_lines=0, n_hits=0)
                ratio = round(n_hits/float(n_lines) if n_lines > 0 else 0, 4)
                el.set('line-rate', str(ratio))
                # Adding another attribute to this: number of lines
                el.set('nlines', str(n_lines))

                n_lines += before_lines
                n_hits += before_hits

            if el.tag == 'line':
                n_lines += 1
                n_hits += int(el.get('hits'))  # will either be 0 or 1
                continue

            # Recusively process the rest of the tree
            (n_lines, n_hits) = self.calculate_coverage(el, n_lines, n_hits)

        return (n_lines, n_hits)


if __name__ == '__main__':
    r = CoberturaCombiner(('functional_coverage.xml', 'unit_coverage.xml')).combine()
    f = open('output.xml', 'w')
    f.write(r)
    f.close()

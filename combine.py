import xml.etree.ElementTree as et
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
        for r in self.roots[1:]:
            # Combine each element with the first one, and update that
            self.combine_element(self.roots[0], r)

        result_xml = self.roots[0]
        #self.calculate_line_coverage(result_xml)
        # Return the string representation
        return et.tostring(self.roots[0])

    def _create_mapping_key(self, element):
        return '{0}:{1}'.format(element.tag, 
                                str([item for item in element.items()
                                    if 'line-rate' not in item 
                                    and 'hits' not in item]))

    def _get_element_item_value(self, element, item):
        val = dict(element.items())[item]
        
        # try saving as an int
        try:
            val = int(val)
        except ValueError:
            # if it's not an int, return a string
            pass

        return val

    def _set_element_item_value(self, element, item, value):
        for tup in element.items():
            if item in tup:
                tup = (item, str(value))
                break

    def combine_element(self, one, other):
        """
        This function recursively updates either the text or the children
        of an element if another element is found in `one`, or adds it from
        `other` if not found.

        Going to need a bit of work to just turn 0's to 1's on conflict.
        """
        # TODO: FIX THIS. IT ISN"T KEEPING 1's from utnit tests and putting them in functional tests


        # Create a mapping from tag name to element
        mapping = { self._create_mapping_key(el): el for el in one }
        #pdb.set_trace()

        for el in other:
            key = self._create_mapping_key(el)
            try:
                if len(el) == 0:
                    if mapping[key] is not None and el.tag == 'line':
                        one_val = self._get_element_item_value(mapping.values()[0], 'hits')
                        other_val = self._get_element_item_value(el, 'hits')
                        new_val = max(one_val, other_val)

                        if one_val != other_val:
                            print "one: %s, other: %s, new: %s" % (one_val, other_val, new_val)
                        hit = max(self._get_element_item_value(mapping.values()[0],'hits'),
                                  self._get_element_item_value(el,'hits'))

                        self._set_element_item_value(mapping.values()[0], 'hits', hit)
                        # TODO: NEED TO FIGURE OUT HOW TO SET THE VALuE OF THE ORIGINAL

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

    def calculate_line_coverage(self, root, n_lines=0, n_hits=0):
        """
        This function goes through the document and updates the 
        coverage numbers for each module in the document

        Need to pass in the coverage list too
        """
        # Grab only the elements which have something valuable to contribute
        gen_root = (e for e in root if len(e.getchildren()) > 0 or len(e.items()) > 0)
        for el in gen_root:
            # Check for line-rate
            # optimize this (remove the for loop)
            for tup in el.items():
                if el.tag == 'class' and 'line-rate' in tup:
                    # count the line coverage, here we need to "start over" counting
                    (n_lines, n_hits) = self.calculate_line_coverage(el, n_lines=0, n_hits=0)
                    ratio = n_hits/float(n_lines) if n_lines > 0 else 0
                    old_ratio = self._get_element_item_value(el, 'line-rate')
                    if float(old_ratio) != round(float(ratio), 4):
                        print "old line coverage: %s" % old_ratio
                        print "new line coverage: %s, n_hits: %s, n_lines: %s" % (round(float(ratio), 4), n_hits, n_lines)
                    self._set_element_item_value(el, 'line-rate', ratio)

            if el.tag == 'line':
                n_lines += 1
                n_hits += self._get_element_item_value(el, 'hits')  # will either be 0 or 1
                continue

            # Recusively process the rest of the tree
            # not sure this is being used
            (n_lines, n_hits) = self.calculate_line_coverage(el, n_lines, n_hits)

        return (n_lines, n_hits)


if __name__ == '__main__':
    r = CoberturaCombiner(('functional_coverage.xml3', 'unit_coverage.xml3')).combine()
    #r = CoberturaCombiner(('functional_coverage.xml', 'unit_coverage.xml2')).combine()
    #r = CoberturaCombiner(('functional_coverage.xml', 'unit_coverage.xml')).combine()
    f = open('output.xml', 'w')
    f.write(r)
    f.close()

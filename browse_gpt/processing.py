from bs4.element import NavigableString, Tag
from bs4 import BeautifulSoup
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver import Chrome
from selenium.webdriver.common.by import By
from undetected_chromedriver.webelement import WebElement
import numpy as np
from typing import List, Set, Tuple, Dict
import logging

MIN_CLASS_OVERLAP = 6  # test cases so far min=5, max=28
MIN_NUM_MATCHES = 3

logger = logging.getLogger(__name__)


def adjacency_matrix_to_groups(sections: List["DecoratedSoup"], adj: np.ndarray) -> Tuple[List[List["DecoratedSoup"]], np.ndarray]:
    # gather element groups
    element_groups = []
    element_group_assignment = np.zeros(len(sections), np.int64) - 1
    for i in range(len(sections)):
        if element_group_assignment[i] < 0:
            group_members, = np.where(adj[i])
            assigned = False
            for j in group_members:
                if j >= i:
                    break

                # set i = j
                element_group_assignment[i] = element_group_assignment[j]
                element_groups[element_group_assignment[i]] += [sections[i]]
                assert sum([len(g) for g in element_groups]) == i + 1, "1"
                assigned = True
                break
                    
            # no match with previously seen elements
            if not assigned:
                # add new group
                element_group_assignment[i] = len(element_groups)
                element_groups += [[sections[i]]]
                assert sum([len(g) for g in element_groups]) == i + 1, "2"
            
        assert sum([len(g) for g in element_groups]) == i + 1, "3"
        
    assert sum([len(g) for g in element_groups]) == len(sections), "4"
    
    return element_groups, element_group_assignment


# TODO using columnwise max overlap as minimum
#      add reference to same-class group in extracted context for later insertion of choice description
def group_sections_by_class_overlap(
        sections: List["DecoratedSoup"],
        all_classes: List[Set[str]],
        min_overlap: int = MIN_CLASS_OVERLAP,
        min_num_matches: int = MIN_NUM_MATCHES,
) -> Tuple[List[List[str]], Dict["DecoratedSoup", int], np.ndarray]:
    # compute pairwise class overlap
    pairwise_class_overlap = np.ndarray([len(sections)] * 2)
    for i, (_, classes) in enumerate(zip(sections, all_classes)):
        for j, (_, classes_) in enumerate(zip(sections, all_classes)):
            pairwise_class_overlap[i, j] = len(classes.intersection(classes_))
    
    # naive: fixed overlap threshold
    element_match = pairwise_class_overlap >= min_overlap
    diag_filter = ~np.diag(np.ones(pairwise_class_overlap.shape[0])).astype('bool')
    assert pairwise_class_overlap.shape[0]
    global max_cls_overlap
    try:
        curr_max = pairwise_class_overlap[diag_filter].max()
        max_cls_overlap = max(max_cls_overlap, curr_max)
    except:
        logger.debug(pairwise_class_overlap.shape)
    logger.debug(curr_max)
    
    element_groups, element_group_assignment = adjacency_matrix_to_groups(sections, element_match)

    if min_num_matches > 1:
        group_idx = 0
        new_element_groups = []
        new_element_group_assignment = np.zeros_like(element_group_assignment) - 1
        for g in element_groups:
            in_g_element_mask = np.array([sections[i] in g for i in range(len(element_group_assignment))])
            if 1 < len(g) < min_num_matches:
                new_element_group_assignment[in_g_element_mask] = np.arange(group_idx, group_idx + len(g))
                new_element_groups += [[e] for e in g]
                group_idx += len(g)
            else:
                new_element_group_assignment[in_g_element_mask] = group_idx
                new_element_groups += [g]
                group_idx += 1

        element_groups = new_element_groups
        element_group_assignment = new_element_group_assignment  # TODO debug
        assert np.all(element_group_assignment) >= 0
    
    return element_groups, {e: idx for e, idx in zip(sections, element_group_assignment)}, element_match


def format_text_newline(t: str) -> str:
    return f'\n'.join([t_.strip() for t_ in t.split('\n') if t_.strip()]).strip()


def recurse_get_classes(s: Tag) -> Set[str]:
    classes = set()
    if s.attrs.get('class'):
        classes.add(' '.join(s.attrs['class']))
    for c in s.children:
        if not isinstance(c, NavigableString):
            classes = classes.union(recurse_get_classes(c))
    return classes


def get_decorated_elem(driver: Chrome, soup: Tag, parent_xpath: str, tag: str, tag_index: int) -> "DecoratedSoup":
    try:
        xpath = parent_xpath + f'/{tag}[{tag_index + 1}]'
        driver_elem = driver.find_element(by=By.XPATH, value=xpath)
    except NoSuchElementException:
        xpath = parent_xpath + f'/*[name()="{tag}"][{tag_index + 1}]'
        try:
            driver_elem = driver.find_element(by=By.XPATH, value=xpath)
        except NoSuchElementException:
            return None

    a = DecoratedSoup(soup, xpath=xpath, driver_elem=driver_elem)
    assert isinstance(a, DecoratedSoup)
    assert a.is_live is not None
    return a


def extract_context(s: Tag, attrs: List[str] = ['aria-label', 'placeholder']) -> Tuple[str, Dict[str, str]]:
    attr_dict = {}
    for attr in attrs:
        if attr in s.attrs:
            attr_dict[attr] = s.attrs[attr]
    text = ''
    for c in s.children:
        if type(c) == NavigableString:
            text += '\n' + format_text_newline(str(c))
    return text.strip(), attr_dict


def extract_and_format_context(s: Tag, attrs: List[str] = ['aria-label', 'placeholder']) -> str:
    context = ''
    text, attr_dict = extract_context(s, attrs=attrs)
    for attr in attr_dict:
        context += '\n' + f'{attr}: {attr_dict[attr]}'
    context += '\n' + text
    return context.strip()


# TODO return DecoratedSoup elements list to get xpath for later reference
def recurse_get_context(
    driver: Chrome,
    ds: "DecoratedSoup",
    attrs: List[str] = ['aria-label', 'placeholder'],
    xpath: str = '/html',
) -> Tuple[List[str], List["DecoratedSoup"], List[List["DecoratedSoup"]]]:
    context = extract_and_format_context(ds.soup, attrs=attrs)
    if context:
        return [context], [ds], []
    descendent_context = []
    class_sets = []
    ds_elems = []
    ds_elem_groups = []
    elem_groups: List[List[DecoratedSoup]] = []
    live_children = []
    tag_idxs = {}
    for c in ds.soup.children:
        if not isinstance(c, NavigableString):
            if c.name not in tag_idxs:
                tag_idxs[c.name] = 0
            dc: DecoratedSoup = get_decorated_elem(driver=driver, soup=c, parent_xpath=xpath, tag=c.name, tag_index=tag_idxs[c.name])
            if dc is None:
                logger.error(f"Failed to find element for xpath: {xpath}/{c.name}[{tag_idxs[c.name]}]")
                continue
            tag_idxs[c.name] += 1
            if dc.is_live():
                class_sets += [recurse_get_classes(c)]
                live_children += [dc]
    
    if len(live_children) > 1:
        # check for same-class groups
        elem_groups, _, _ = group_sections_by_class_overlap(live_children, class_sets)
        logger.debug(ds.soup.name)
        logger.debug([len(g) for g in elem_groups])
    elif len(live_children) > 0:
        elem_groups = [live_children]

    for g in elem_groups:
        dc, *_ = g
        if len(g) == 1:
            logger.debug(f'recursing to {str(dc.soup)[:30]}')
            context, elems, elem_groups_ = recurse_get_context(driver=driver, ds=dc, xpath=dc.xpath)
            descendent_context += context
            ds_elems += elems
            ds_elem_groups += elem_groups_
        else:
            soup_group = DecoratedSoupGroup(g)
            descendent_context += ['']
            ds_elem_groups += [soup_group]
            ds_elems += [soup_group]
            
    logger.debug(f'found groups for {ds.soup.name}: {[len(g) for g in elem_groups]}')

    return descendent_context, ds_elems, ds_elem_groups


class DecoratedSoup:
    def __init__(self, soup: Tag, xpath: str = '/', driver_elem: WebElement = None):
        self.soup = soup
        self.context = ''
        self.driver_elem = driver_elem
        self.xpath = xpath
        
    def is_live(self) -> bool:
        return self.driver_elem.is_displayed()


class DecoratedSoupGroup(DecoratedSoup):
    def __init__(self, elems: List[DecoratedSoup]):
        self.elems = list(elems)
        super().__init__(self.elems[0], self.elems[0].xpath, self.elems[0].driver_elem)
        self.group_xpath = "/".join(self.xpath.split("/")[:-1])


def _test():
    import os
    from cache.util import load_from_path, get_load_path, get_workdir, PAGE_CONTENT_FILENAME
    from browser.chromedriver import start_driver

    workdir = get_workdir()
    test_content = load_from_path(
        page_id="fandango.com",
        session_id="fandango",
        cache_dir="example",
        filename=PAGE_CONTENT_FILENAME,
    )
    test_content_path = get_load_path(
        page_id="fandango.com",
        session_id="fandango",
        cache_dir="example",
        filename=PAGE_CONTENT_FILENAME,
    )
    root_elem = BeautifulSoup(test_content).find()
    driver = start_driver()
    driver.get(f"file://{os.path.join(workdir, test_content_path)}")
    text_list, elems, elem_groups = recurse_get_context(driver=driver, ds=root_elem)
    print("\n".join(text_list))

    # check text context of same group elements
    for i, g in enumerate(elem_groups):
        print(f"Group {i} -----")
        for e in g.elems[:2]:
            print(e.soup.get_text())
            print("-----")

    # verify functionality of group context insertion
    assert len(text_list) == len(elems)


if __name__ == "__main__":
    _test()

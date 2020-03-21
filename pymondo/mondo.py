"""
parse mondo
"""
import json
from pathlib import Path
from enum import Enum
from typing import List

from cnorm.chain import Chain

from .downloader import Downloader
from .data import find


class Scope(Enum):
    EXACT = 1
    BROAD = 2
    NARROW = 3
    RELATED = 4


def parse_synonym(data):
    name = data['val']
    xrefs = data['xrefs']
    pred = data['pred']
    if pred == 'hasExactSynonym':
        scope = Scope.EXACT
    elif pred == 'hasBroadSynonym':
        scope = Scope.BROAD
    elif pred == 'hasNarrowSynonym':
        scope = Scope.NARROW
    elif pred == 'hasRelatedSynonym':
        scope = Scope.RELATED
    else:
        raise ValueError('unknown scope was detected')
    return Synonym(name, scope, xrefs)


class Synonym(object):
    def __init__(self, name: str, scope: Scope, xrefs: List[str]):
        self.name = name
        self.scope = scope
        self.xrefs = xrefs

    def __repr__(self):
        return '{}\t{}\t{}'.format(self.name, self.scope.name, ' '.join(['[{}]'.format(x) for x in self.xrefs]))


class MondoNode(object):
    def __init__(self, _id: str, name: str, synonyms: List[Synonym], xrefs: List[str], deprecated: bool=False):
        self.id = _id
        self.name = name
        self.synonyms = synonyms
        self.xrefs = xrefs
        self.deprecated = deprecated
        self.parents = set()
        self.children = set()

    def __repr__(self):
        lines = [
            'id: {}'.format(self.id),
            'name: {}'.format(self.name),
        ]
        if self.synonyms:
            lines += ['synonyms']
            for synonym in self.synonyms:
                lines += ['--{}'.format(synonym.__repr__())]
        if self.xrefs:
            lines += ['xrefs']
            for xref in self.xrefs:
                lines += ['--{}'.format(xref)]
        if self.deprecated:
            lines += ['deprecated: True']

        return '\n'.join(lines)


class Mondo(object):
    def __init__(self, resource: str='mondo'):
        self.mondo = {}
        self.mapper = {}
        self.fp = find(resource)
        if not self.fp.exists():
            downloader = Downloader()
            downloader.download(resource)
        self.read(self.fp)

    def __len__(self):
        return len(self.mondo)

    def __iter__(self):
        return iter(self.mondo.values())

    def __getitem__(self, item):
        return self.mondo[item]

    def read(self, fp: Path):
        with fp.open() as f:
            graphs = json.load(f)['graphs']
        mondo_graph = graphs[0]
        for node in mondo_graph['nodes']:
            _id = node['id'].split('/')[-1]
            name = node.get('lbl')

            meta = node.get('meta')
            if meta is not None and 'synonyms' in meta:
                synonyms = sorted([parse_synonym(s) for s in node['meta']['synonyms']], key=lambda x: x.name.lower())
            else:
                synonyms = []

            if meta is not None and 'xrefs' in node['meta']:
                xrefs = sorted([x['val'] for x in node['meta']['xrefs']])
            else:
                xrefs = []

            if meta is not None and meta.get('deprecated'):
                deprecated = True
            else:
                deprecated = False

            mondo_node = MondoNode(
                _id=_id,
                name=name,
                synonyms=synonyms,
                xrefs=xrefs,
                deprecated=deprecated,
            )
            self.mondo[_id] = mondo_node

        for edge in mondo_graph['edges']:
            if not edge['pred'] == 'is_a':
                continue
            child = edge['sub'].split('/')[-1]
            parent = edge['obj'].split('/')[-1]
            if not (child.startswith('MONDO') and parent.startswith('MONDO')):
                continue
            self.mondo[child].parents.add(parent)
            self.mondo[parent].children.add(child)

    def make_mapper(
            self, chain: Chain=Chain(),
            ignore_synonym: bool=True, allowed_scope_list: List[Scope]=Scope.EXACT,
            ignore_deprecated: bool=True
    ):
        """return the list of mondos which contain the pattern
        :param chain: chain of rules
        :param ignore_synonym:
        :param allowed_scope_list:
        :param ignore_deprecated:
        :return:
        """
        mapper = {}
        for _id, mondo_node in self.mondo.items():
            if ignore_deprecated and mondo_node.deprecated:
                continue

            text = chain.apply(mondo_node.name)
            mapper.setdefault(text, set())
            mapper[text].add(_id)

            if ignore_synonym:
                continue

            for synonym in mondo_node.synonyms:
                if synonym.scope not in allowed_scope_list:
                    continue
                text = chain.apply(synonym.name)
                mapper[text].add(_id)
        self.mapper = mapper

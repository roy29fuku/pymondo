"""
parse mondo
"""
import json
from pathlib import Path
from enum import Enum
from typing import List

from cnorm.chain import Chain

from .downloader import Downloader
from .data import find, default_data_dir


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
    def __init__(self, resource: str='mondo', data_dir: Path=default_data_dir):
        self.mondo = {}
        self.name2mondoids = {}
        self.rid2mondoids = {}
        self.fp = find(resource, data_dir)
        if not self.fp.exists():
            downloader = Downloader(data_dir)
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

    def make_name2mondoids(
            self, chain: Chain=Chain(),
            allowed_scope_list: List[Scope]=None,
            allow_deprecated: bool=False
    ):
        """make a dictionary which maps noramalized name to mondo ids
        :param chain: chain of rules
        :param allowed_scope_list:
        :param allow_deprecated:
        :return:
        """
        name2mondoids = {}
        for _id, mondo_node in self.mondo.items():
            if mondo_node.deprecated and not allow_deprecated:
                continue

            text = chain.apply(mondo_node.name)
            name2mondoids.setdefault(text, set())
            name2mondoids[text].add(_id)

            if not allowed_scope_list:
                continue

            for synonym in mondo_node.synonyms:
                if synonym.scope not in allowed_scope_list:
                    continue
                text = chain.apply(synonym.name)
                name2mondoids.setdefault(text, set())
                name2mondoids[text].add(_id)
        self.name2mondoids = name2mondoids

    def make_rid2mondoids(
            self,
            allowed_scope_list: List[Scope]=None,
            allow_deprecated: bool=False
    ):
        """make a dictionary which maps resource id to mondo ids
        :param allowed_scope_list:
        :param allow_deprecated:
        :return:
        """
        rid2mondoids = {}
        for _id, mondo_node in self.mondo.items():
            if mondo_node.deprecated and not allow_deprecated:
                continue

            for xref in mondo_node.xrefs:
                rid2mondoids.setdefault(xref, set())
                rid2mondoids[xref].add(_id)

            if not allowed_scope_list:
                continue

            for synonym in mondo_node.synonyms:
                if synonym.scope not in allowed_scope_list:
                    continue
                for xref in synonym.xrefs:
                    rid2mondoids.setdefault(xref, set())
                    rid2mondoids[xref].add(_id)
        self.rid2mondoids = rid2mondoids
